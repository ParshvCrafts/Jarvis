"""
Essay Generation Workflow for JARVIS Scholarship Module.

Implements the agentic workflow:
INIT → GATHER → RAG_SEARCH → GENERATE → REVIEW → ADJUST → OUTPUT → COMPLETE
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

from .models import (
    EligibilityProfile,
    Scholarship,
    ScholarshipQuestion,
    GeneratedEssay,
    PastEssay,
)
from .prompts import PromptTemplates
from .rag import ScholarshipRAG, RAGContext


class WorkflowState(Enum):
    """States in the essay generation workflow."""
    INIT = "init"
    GATHER = "gather"
    RAG_SEARCH = "rag_search"
    GENERATE = "generate"
    REVIEW = "review"
    ADJUST = "adjust"
    OUTPUT = "output"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class GenerationConfig:
    """Configuration for essay generation."""
    # LLM settings
    primary_llm: str = "groq"
    fallback_llm: str = "gemini"
    max_attempts: int = 3
    
    # Word count settings
    word_tolerance: int = 5  # Allow ±5 words
    
    # RAG settings
    num_similar_essays: int = 5
    num_statement_sections: int = 3
    num_profile_sections: int = 5
    prefer_winning_essays: bool = True
    
    # Quality settings
    min_quality_score: float = 7.0
    auto_adjust: bool = True


@dataclass
class GenerationState:
    """State during essay generation."""
    # Current state
    state: WorkflowState = WorkflowState.INIT
    
    # Input
    scholarship: Optional[Scholarship] = None
    question: Optional[ScholarshipQuestion] = None
    profile: Optional[EligibilityProfile] = None
    
    # RAG context
    rag_context: Optional[RAGContext] = None
    
    # Generation
    prompt: str = ""
    generated_essay: str = ""
    word_count: int = 0
    target_word_count: int = 0
    
    # Review
    quality_score: float = 0.0
    review_feedback: str = ""
    
    # Adjustments
    adjustment_count: int = 0
    adjustment_history: List[str] = field(default_factory=list)
    
    # Output
    final_essay: Optional[GeneratedEssay] = None
    google_doc_url: Optional[str] = None
    
    # Errors
    error: Optional[str] = None
    
    # Progress
    progress_percent: float = 0.0
    current_step: str = ""
    messages: List[str] = field(default_factory=list)


class EssayGenerator:
    """
    Agentic essay generation workflow.
    
    Generates high-quality, personalized scholarship essays using:
    - RAG retrieval of similar winning essays
    - Advanced prompt engineering
    - Iterative word count adjustment
    - Quality review and refinement
    """
    
    def __init__(
        self,
        llm_router=None,
        rag: Optional[ScholarshipRAG] = None,
        config: Optional[GenerationConfig] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ):
        """
        Initialize essay generator.
        
        Args:
            llm_router: LLM router for generation
            rag: RAG system for context retrieval
            config: Generation configuration
            progress_callback: Callback for progress updates
        """
        self.llm_router = llm_router
        self.rag = rag
        self.config = config or GenerationConfig()
        self.progress_callback = progress_callback
    
    def _update_progress(self, message: str, percent: float):
        """Update progress."""
        if self.progress_callback:
            self.progress_callback(message, percent)
        logger.info(f"[{percent:.0f}%] {message}")
    
    def _count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())
    
    async def _call_llm(self, prompt: str, provider: Optional[str] = None) -> str:
        """Call LLM with prompt."""
        if not self.llm_router:
            raise ValueError("LLM router not configured")
        
        try:
            response = await self.llm_router.route(
                prompt,
                provider=provider or self.config.primary_llm,
            )
            return response.get("response", "")
        except Exception as e:
            logger.warning(f"Primary LLM failed: {e}, trying fallback")
            try:
                response = await self.llm_router.route(
                    prompt,
                    provider=self.config.fallback_llm,
                )
                return response.get("response", "")
            except Exception as e2:
                logger.error(f"Fallback LLM also failed: {e2}")
                raise
    
    # =========================================================================
    # Workflow Steps
    # =========================================================================
    
    async def _init_step(self, state: GenerationState) -> GenerationState:
        """Initialize generation state."""
        self._update_progress("📋 Initializing essay generation...", 5)
        state.state = WorkflowState.INIT
        state.current_step = "Initialization"
        
        # Validate inputs
        if not state.scholarship:
            state.error = "No scholarship provided"
            state.state = WorkflowState.ERROR
            return state
        
        if not state.question:
            state.error = "No question provided"
            state.state = WorkflowState.ERROR
            return state
        
        # Set target word count
        state.target_word_count = state.question.word_limit
        
        state.messages.append(f"Generating essay for: {state.scholarship.name}")
        state.messages.append(f"Question: {state.question.question_text[:100]}...")
        state.messages.append(f"Word limit: {state.target_word_count}")
        
        return state
    
    async def _gather_step(self, state: GenerationState) -> GenerationState:
        """Gather all necessary context."""
        self._update_progress("📚 Gathering context...", 15)
        state.state = WorkflowState.GATHER
        state.current_step = "Gathering Context"
        
        # Ensure we have a profile
        if not state.profile:
            state.profile = EligibilityProfile()  # Use defaults
        
        state.messages.append(f"Profile loaded: {state.profile.name}")
        
        return state
    
    async def _rag_search_step(self, state: GenerationState) -> GenerationState:
        """Search for relevant context using RAG."""
        self._update_progress("🔍 Searching similar essays...", 25)
        state.state = WorkflowState.RAG_SEARCH
        state.current_step = "RAG Search"
        
        if not self.rag:
            state.messages.append("RAG not available - generating without past essays")
            state.rag_context = RAGContext(query=state.question.question_text)
            return state
        
        try:
            state.rag_context = await self.rag.retrieve(
                question=state.question.question_text,
                scholarship_name=state.scholarship.name,
                num_essays=self.config.num_similar_essays,
                num_statements=self.config.num_statement_sections,
                num_profiles=self.config.num_profile_sections,
                prefer_winners=self.config.prefer_winning_essays,
            )
            
            num_essays = len(state.rag_context.similar_essays)
            winning = sum(1 for e, _ in state.rag_context.similar_essays 
                         if e.outcome.value == "won")
            
            state.messages.append(f"Found {num_essays} similar essays ({winning} winners)")
            state.messages.append(f"Themes identified: {', '.join(state.rag_context.themes)}")
            
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            state.messages.append(f"RAG search failed: {e}")
            state.rag_context = RAGContext(query=state.question.question_text)
        
        return state
    
    async def _generate_step(self, state: GenerationState) -> GenerationState:
        """Generate the essay."""
        self._update_progress("✍️ Generating essay...", 45)
        state.state = WorkflowState.GENERATE
        state.current_step = "Generating Essay"
        
        # Build prompt
        rag_context = state.rag_context.to_prompt_context() if state.rag_context else {}
        
        prompt_vars = {
            # Scholarship info
            "scholarship_name": state.scholarship.name,
            "scholarship_description": state.scholarship.description,
            "award_amount": state.scholarship.amount_text or f"${state.scholarship.amount:,.0f}",
            "provider": state.scholarship.provider,
            
            # Question
            "question": state.question.question_text,
            "word_limit": state.target_word_count,
            
            # Profile
            "name": state.profile.name,
            "major": state.profile.major,
            "university": state.profile.university,
            "year": state.profile.year,
            "field": state.profile.field.value if hasattr(state.profile.field, 'value') else state.profile.field,
            "achievements": "\n".join(f"- {a}" for a in state.profile.achievements) or "See past essays",
            "experience": "\n".join(f"- {e}" for e in state.profile.work_experience) or "See past essays",
            "leadership": "\n".join(f"- {l}" for l in state.profile.leadership_roles) or "See past essays",
            
            # RAG context
            "rag_essays": rag_context.get("similar_essays", "No similar essays available"),
            "rag_profile": rag_context.get("profile", "No profile sections available"),
            "rag_statement": rag_context.get("personal_statement", "No personal statement available"),
        }
        
        state.prompt = PromptTemplates.format_template("master_essay", **prompt_vars)
        
        # Generate essay
        try:
            state.generated_essay = await self._call_llm(state.prompt)
            state.word_count = self._count_words(state.generated_essay)
            
            state.messages.append(f"Generated essay: {state.word_count} words")
            
        except Exception as e:
            state.error = f"Generation failed: {e}"
            state.state = WorkflowState.ERROR
            return state
        
        return state
    
    async def _review_step(self, state: GenerationState) -> GenerationState:
        """Review the generated essay."""
        self._update_progress("📝 Reviewing essay...", 65)
        state.state = WorkflowState.REVIEW
        state.current_step = "Reviewing"
        
        # Check word count
        word_diff = state.word_count - state.target_word_count
        
        if abs(word_diff) <= self.config.word_tolerance:
            state.messages.append(f"✓ Word count OK: {state.word_count}/{state.target_word_count}")
        elif word_diff > 0:
            state.messages.append(f"⚠ Over word limit by {word_diff} words")
        else:
            state.messages.append(f"⚠ Under word limit by {abs(word_diff)} words")
        
        # Quality review (optional - can be expensive)
        # For now, just do basic checks
        state.quality_score = self._basic_quality_check(state.generated_essay, state.question.question_text)
        state.messages.append(f"Quality score: {state.quality_score:.1f}/10")
        
        return state
    
    def _basic_quality_check(self, essay: str, question: str) -> float:
        """Basic quality check without LLM."""
        score = 5.0  # Base score
        
        # Length check
        words = self._count_words(essay)
        if words >= 50:
            score += 1.0
        if words >= 100:
            score += 0.5
        
        # Has paragraphs
        if essay.count("\n\n") >= 1:
            score += 0.5
        
        # Doesn't start with clichés
        cliches = ["growing up", "ever since i was", "i have always"]
        if not any(essay.lower().startswith(c) for c in cliches):
            score += 0.5
        
        # Has specific details (numbers, names)
        if re.search(r'\d+', essay):
            score += 0.5
        
        # Reasonable sentence variety
        sentences = essay.split('.')
        if len(sentences) >= 3:
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
            if 10 <= avg_len <= 25:
                score += 0.5
        
        # Contains question keywords
        question_words = set(question.lower().split())
        essay_words = set(essay.lower().split())
        overlap = len(question_words & essay_words)
        if overlap >= 3:
            score += 0.5
        
        return min(score, 10.0)
    
    async def _adjust_step(self, state: GenerationState) -> GenerationState:
        """Adjust essay if needed (word count, quality)."""
        self._update_progress("🔧 Adjusting essay...", 75)
        state.state = WorkflowState.ADJUST
        state.current_step = "Adjusting"
        
        word_diff = state.word_count - state.target_word_count
        
        # Check if adjustment needed
        if abs(word_diff) <= self.config.word_tolerance:
            state.messages.append("No adjustment needed")
            return state
        
        if state.adjustment_count >= self.config.max_attempts:
            state.messages.append(f"Max adjustments reached ({self.config.max_attempts})")
            return state
        
        state.adjustment_count += 1
        
        try:
            if word_diff > 0:
                # Need to reduce
                state.messages.append(f"Reducing from {state.word_count} to {state.target_word_count}...")
                
                prompt = PromptTemplates.format_template(
                    "word_reduction",
                    current_essay=state.generated_essay,
                    current_words=state.word_count,
                    target_words=state.target_word_count,
                )
                
                state.generated_essay = await self._call_llm(prompt)
                state.word_count = self._count_words(state.generated_essay)
                state.adjustment_history.append(f"Reduced to {state.word_count} words")
                
            else:
                # Need to expand
                state.messages.append(f"Expanding from {state.word_count} to {state.target_word_count}...")
                
                # Get additional context for expansion
                additional_context = ""
                if state.rag_context:
                    additional_context = state.rag_context.get_profile_text()
                
                prompt = PromptTemplates.format_template(
                    "word_expansion",
                    current_essay=state.generated_essay,
                    current_words=state.word_count,
                    target_words=state.target_word_count,
                    additional_context=additional_context or "Use more specific details and examples",
                )
                
                state.generated_essay = await self._call_llm(prompt)
                state.word_count = self._count_words(state.generated_essay)
                state.adjustment_history.append(f"Expanded to {state.word_count} words")
            
            state.messages.append(f"Adjusted to {state.word_count} words")
            
            # Check if more adjustment needed
            new_diff = state.word_count - state.target_word_count
            if abs(new_diff) > self.config.word_tolerance and state.adjustment_count < self.config.max_attempts:
                return await self._adjust_step(state)
                
        except Exception as e:
            state.messages.append(f"Adjustment failed: {e}")
        
        return state
    
    async def _output_step(self, state: GenerationState) -> GenerationState:
        """Prepare final output."""
        self._update_progress("📄 Preparing output...", 90)
        state.state = WorkflowState.OUTPUT
        state.current_step = "Output"
        
        # Create GeneratedEssay object
        state.final_essay = GeneratedEssay(
            scholarship_id=state.scholarship.id,
            scholarship_name=state.scholarship.name,
            question_id=state.question.id,
            question_text=state.question.question_text,
            essay_text=state.generated_essay,
            word_count=state.word_count,
            target_word_count=state.target_word_count,
            llm_used=self.config.primary_llm,
            prompt_template="master_essay",
            similar_essays_used=[
                e.id for e, _ in (state.rag_context.similar_essays if state.rag_context else [])
            ],
            revision_count=state.adjustment_count,
            quality_score=state.quality_score,
        )
        
        state.messages.append("Essay ready for output")
        
        return state
    
    async def _complete_step(self, state: GenerationState) -> GenerationState:
        """Complete the workflow."""
        self._update_progress("✅ Essay generation complete!", 100)
        state.state = WorkflowState.COMPLETE
        state.current_step = "Complete"
        state.progress_percent = 100
        
        state.messages.append(f"Final word count: {state.word_count}/{state.target_word_count}")
        state.messages.append(f"Quality score: {state.quality_score:.1f}/10")
        
        return state
    
    # =========================================================================
    # Main Workflow
    # =========================================================================
    
    async def generate(
        self,
        scholarship: Scholarship,
        question: ScholarshipQuestion,
        profile: Optional[EligibilityProfile] = None,
    ) -> GenerationState:
        """
        Generate an essay for a scholarship question.
        
        Args:
            scholarship: The scholarship
            question: The essay question
            profile: User's eligibility profile
            
        Returns:
            GenerationState with the generated essay
        """
        state = GenerationState(
            scholarship=scholarship,
            question=question,
            profile=profile or EligibilityProfile(),
        )
        
        try:
            # Run workflow steps
            state = await self._init_step(state)
            if state.state == WorkflowState.ERROR:
                return state
            
            state = await self._gather_step(state)
            state = await self._rag_search_step(state)
            state = await self._generate_step(state)
            
            if state.state == WorkflowState.ERROR:
                return state
            
            state = await self._review_step(state)
            
            if self.config.auto_adjust:
                state = await self._adjust_step(state)
            
            state = await self._output_step(state)
            state = await self._complete_step(state)
            
        except Exception as e:
            logger.error(f"Essay generation failed: {e}")
            state.error = str(e)
            state.state = WorkflowState.ERROR
        
        return state
    
    async def generate_all(
        self,
        scholarship: Scholarship,
        profile: Optional[EligibilityProfile] = None,
    ) -> List[GenerationState]:
        """
        Generate essays for all questions in a scholarship.
        
        Args:
            scholarship: The scholarship with questions
            profile: User's eligibility profile
            
        Returns:
            List of GenerationState for each question
        """
        results = []
        
        for i, question in enumerate(scholarship.questions):
            self._update_progress(
                f"Generating essay {i+1}/{len(scholarship.questions)}...",
                (i / len(scholarship.questions)) * 100
            )
            
            state = await self.generate(scholarship, question, profile)
            results.append(state)
        
        return results
    
    def get_summary(self, state: GenerationState) -> str:
        """Get human-readable summary of generation."""
        if state.state == WorkflowState.ERROR:
            return f"❌ Generation failed: {state.error}"
        
        if state.state != WorkflowState.COMPLETE:
            return f"⏳ Generation in progress: {state.current_step}"
        
        lines = [
            "✅ **Essay Generated Successfully!**",
            "",
            f"**Scholarship:** {state.scholarship.name}",
            f"**Question:** {state.question.question_text[:100]}...",
            "",
            f"**Word Count:** {state.word_count}/{state.target_word_count}",
            f"**Quality Score:** {state.quality_score:.1f}/10",
            f"**Adjustments Made:** {state.adjustment_count}",
            "",
            "**Essay Preview:**",
            state.generated_essay[:500] + "..." if len(state.generated_essay) > 500 else state.generated_essay,
        ]
        
        return "\n".join(lines)
