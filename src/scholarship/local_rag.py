"""
Local RAG System using ChromaDB for JARVIS Scholarship Module.

Provides full RAG functionality when Supabase is unavailable:
- ChromaDB vector storage
- Persistent local database
- Same interface as Supabase RAG
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger

from .models import PastEssay, PersonalStatement, PersonalProfile, EssayOutcome

# Try importing ChromaDB
CHROMADB_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    logger.debug("chromadb not installed - local RAG limited")


class LocalRAGStore:
    """
    Local RAG storage using ChromaDB.
    
    Provides persistent vector storage for:
    - Past essays
    - Personal statements
    - Personal profiles
    
    Falls back to in-memory storage if ChromaDB unavailable.
    """
    
    COLLECTION_ESSAYS = "scholarship_essays"
    COLLECTION_STATEMENTS = "personal_statements"
    COLLECTION_PROFILES = "personal_profiles"
    
    def __init__(
        self,
        persist_dir: str = "data/scholarship_rag",
        embedding_function=None,
    ):
        """
        Initialize local RAG store.
        
        Args:
            persist_dir: Directory for persistent storage
            embedding_function: Optional custom embedding function
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self._client = None
        self._essays_collection = None
        self._statements_collection = None
        self._profiles_collection = None
        self._embedding_fn = embedding_function
        
        # In-memory fallback
        self._memory_essays: List[Tuple[PastEssay, List[float]]] = []
        self._memory_statements: List[Tuple[PersonalStatement, List[float]]] = []
        self._memory_profiles: List[Tuple[PersonalProfile, List[float]]] = []
        
        self._init_chromadb()
    
    def _init_chromadb(self):
        """Initialize ChromaDB client and collections."""
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not available - using in-memory storage")
            return
        
        try:
            # Create persistent client
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
            
            # Get or create collections
            self._essays_collection = self._client.get_or_create_collection(
                name=self.COLLECTION_ESSAYS,
                metadata={"description": "Past scholarship essays"}
            )
            
            self._statements_collection = self._client.get_or_create_collection(
                name=self.COLLECTION_STATEMENTS,
                metadata={"description": "Personal statement sections"}
            )
            
            self._profiles_collection = self._client.get_or_create_collection(
                name=self.COLLECTION_PROFILES,
                metadata={"description": "Personal profile sections"}
            )
            
            logger.info(f"ChromaDB initialized at {self.persist_dir}")
            logger.info(
                f"Collections: {self._essays_collection.count()} essays, "
                f"{self._statements_collection.count()} statements, "
                f"{self._profiles_collection.count()} profiles"
            )
            
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            self._client = None
    
    @property
    def is_available(self) -> bool:
        """Check if ChromaDB is available."""
        return self._client is not None
    
    def get_mode(self) -> str:
        """Get current storage mode."""
        if self._client:
            return "chromadb"
        return "memory"
    
    # =========================================================================
    # Essay Operations
    # =========================================================================
    
    def add_essay(
        self,
        essay: PastEssay,
        embedding: List[float],
    ) -> Optional[str]:
        """
        Add a past essay with embedding.
        
        Args:
            essay: PastEssay object
            embedding: Vector embedding
            
        Returns:
            Essay ID if successful
        """
        essay_id = essay.id or f"essay_{datetime.now().timestamp()}"
        
        if self._essays_collection:
            try:
                # Prepare metadata
                metadata = {
                    "scholarship_name": essay.scholarship_name,
                    "question": essay.question or "",
                    "word_count": essay.word_count,
                    "outcome": essay.outcome.value if essay.outcome else "pending",
                    "themes": ",".join(essay.themes) if essay.themes else "",
                    "date_written": essay.date_written.isoformat() if essay.date_written else "",
                }
                
                self._essays_collection.add(
                    ids=[essay_id],
                    embeddings=[embedding],
                    documents=[essay.essay_text],
                    metadatas=[metadata],
                )
                
                logger.debug(f"Added essay to ChromaDB: {essay.scholarship_name}")
                return essay_id
                
            except Exception as e:
                logger.error(f"Failed to add essay to ChromaDB: {e}")
        
        # Fallback to memory
        self._memory_essays.append((essay, embedding))
        return essay_id
    
    def search_essays(
        self,
        query_embedding: List[float],
        limit: int = 5,
        outcome_filter: Optional[EssayOutcome] = None,
    ) -> List[Tuple[PastEssay, float]]:
        """
        Search for similar essays.
        
        Args:
            query_embedding: Query vector
            limit: Maximum results
            outcome_filter: Filter by outcome
            
        Returns:
            List of (essay, similarity) tuples
        """
        if self._essays_collection:
            try:
                # Build where filter
                where_filter = None
                if outcome_filter:
                    where_filter = {"outcome": outcome_filter.value}
                
                results = self._essays_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where=where_filter,
                    include=["documents", "metadatas", "distances"],
                )
                
                essays = []
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    document = results["documents"][0][i]
                    distance = results["distances"][0][i] if results.get("distances") else 0
                    
                    # Convert distance to similarity (ChromaDB uses L2 by default)
                    similarity = 1 / (1 + distance)
                    
                    essay = PastEssay(
                        id=doc_id,
                        scholarship_name=metadata.get("scholarship_name", "Unknown"),
                        question=metadata.get("question", ""),
                        essay_text=document,
                        word_count=metadata.get("word_count", len(document.split())),
                        outcome=EssayOutcome(metadata.get("outcome", "pending")),
                        themes=metadata.get("themes", "").split(",") if metadata.get("themes") else [],
                    )
                    
                    essays.append((essay, similarity))
                
                return essays
                
            except Exception as e:
                logger.error(f"ChromaDB essay search failed: {e}")
        
        # Fallback to memory search
        return self._search_memory_essays(query_embedding, limit, outcome_filter)
    
    def _search_memory_essays(
        self,
        query_embedding: List[float],
        limit: int,
        outcome_filter: Optional[EssayOutcome],
    ) -> List[Tuple[PastEssay, float]]:
        """Search in-memory essays."""
        if not self._memory_essays:
            return []
        
        results = []
        for essay, emb in self._memory_essays:
            if outcome_filter and essay.outcome != outcome_filter:
                continue
            
            similarity = self._cosine_similarity(query_embedding, emb)
            results.append((essay, similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def get_essay_count(self) -> int:
        """Get total essay count."""
        if self._essays_collection:
            return self._essays_collection.count()
        return len(self._memory_essays)
    
    def get_winning_essays(self, limit: int = 10) -> List[PastEssay]:
        """Get winning essays."""
        if self._essays_collection:
            try:
                results = self._essays_collection.get(
                    where={"outcome": "won"},
                    limit=limit,
                    include=["documents", "metadatas"],
                )
                
                essays = []
                for i, doc_id in enumerate(results["ids"]):
                    metadata = results["metadatas"][i]
                    document = results["documents"][i]
                    
                    essay = PastEssay(
                        id=doc_id,
                        scholarship_name=metadata.get("scholarship_name", "Unknown"),
                        question=metadata.get("question", ""),
                        essay_text=document,
                        word_count=metadata.get("word_count", 0),
                        outcome=EssayOutcome.WON,
                    )
                    essays.append(essay)
                
                return essays
                
            except Exception as e:
                logger.error(f"Failed to get winning essays: {e}")
        
        return [e for e, _ in self._memory_essays if e.outcome == EssayOutcome.WON][:limit]
    
    # =========================================================================
    # Personal Statement Operations
    # =========================================================================
    
    def add_statement(
        self,
        statement: PersonalStatement,
        embedding: List[float],
    ) -> Optional[str]:
        """Add a personal statement section."""
        stmt_id = statement.id or f"stmt_{datetime.now().timestamp()}"
        
        if self._statements_collection:
            try:
                metadata = {
                    "section_name": statement.section_name,
                    "themes": ",".join(statement.themes) if statement.themes else "",
                }
                
                self._statements_collection.add(
                    ids=[stmt_id],
                    embeddings=[embedding],
                    documents=[statement.content],
                    metadatas=[metadata],
                )
                return stmt_id
                
            except Exception as e:
                logger.error(f"Failed to add statement: {e}")
        
        self._memory_statements.append((statement, embedding))
        return stmt_id
    
    def search_statements(
        self,
        query_embedding: List[float],
        limit: int = 3,
    ) -> List[Tuple[PersonalStatement, float]]:
        """Search personal statement sections."""
        if self._statements_collection:
            try:
                results = self._statements_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"],
                )
                
                statements = []
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    document = results["documents"][0][i]
                    distance = results["distances"][0][i] if results.get("distances") else 0
                    similarity = 1 / (1 + distance)
                    
                    stmt = PersonalStatement(
                        id=doc_id,
                        section_name=metadata.get("section_name", ""),
                        content=document,
                        themes=metadata.get("themes", "").split(",") if metadata.get("themes") else [],
                    )
                    statements.append((stmt, similarity))
                
                return statements
                
            except Exception as e:
                logger.error(f"Statement search failed: {e}")
        
        # Memory fallback
        if not self._memory_statements:
            return []
        
        results = [
            (stmt, self._cosine_similarity(query_embedding, emb))
            for stmt, emb in self._memory_statements
        ]
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    # =========================================================================
    # Profile Operations
    # =========================================================================
    
    def add_profile(
        self,
        profile: PersonalProfile,
        embedding: List[float],
    ) -> Optional[str]:
        """Add a profile section."""
        profile_id = profile.id or f"profile_{datetime.now().timestamp()}"
        
        if self._profiles_collection:
            try:
                metadata = {
                    "section": profile.section,
                    "category": profile.category or "",
                }
                
                self._profiles_collection.add(
                    ids=[profile_id],
                    embeddings=[embedding],
                    documents=[profile.content],
                    metadatas=[metadata],
                )
                return profile_id
                
            except Exception as e:
                logger.error(f"Failed to add profile: {e}")
        
        self._memory_profiles.append((profile, embedding))
        return profile_id
    
    def search_profiles(
        self,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Tuple[PersonalProfile, float]]:
        """Search profile sections."""
        if self._profiles_collection:
            try:
                results = self._profiles_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"],
                )
                
                profiles = []
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    document = results["documents"][0][i]
                    distance = results["distances"][0][i] if results.get("distances") else 0
                    similarity = 1 / (1 + distance)
                    
                    profile = PersonalProfile(
                        id=doc_id,
                        section=metadata.get("section", ""),
                        content=document,
                        category=metadata.get("category", ""),
                    )
                    profiles.append((profile, similarity))
                
                return profiles
                
            except Exception as e:
                logger.error(f"Profile search failed: {e}")
        
        # Memory fallback
        if not self._memory_profiles:
            return []
        
        results = [
            (profile, self._cosine_similarity(query_embedding, emb))
            for profile, emb in self._memory_profiles
        ]
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        stats = {
            "mode": self.get_mode(),
            "essays": 0,
            "statements": 0,
            "profiles": 0,
        }
        
        if self._essays_collection:
            stats["essays"] = self._essays_collection.count()
            stats["statements"] = self._statements_collection.count()
            stats["profiles"] = self._profiles_collection.count()
        else:
            stats["essays"] = len(self._memory_essays)
            stats["statements"] = len(self._memory_statements)
            stats["profiles"] = len(self._memory_profiles)
        
        return stats
    
    def export_to_json(self, output_path: str) -> str:
        """Export all data to JSON for backup."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "essays": [],
            "statements": [],
            "profiles": [],
        }
        
        # Export essays
        if self._essays_collection:
            results = self._essays_collection.get(include=["documents", "metadatas"])
            for i, doc_id in enumerate(results["ids"]):
                data["essays"].append({
                    "id": doc_id,
                    "metadata": results["metadatas"][i],
                    "content": results["documents"][i],
                })
        
        # Export statements
        if self._statements_collection:
            results = self._statements_collection.get(include=["documents", "metadatas"])
            for i, doc_id in enumerate(results["ids"]):
                data["statements"].append({
                    "id": doc_id,
                    "metadata": results["metadatas"][i],
                    "content": results["documents"][i],
                })
        
        # Export profiles
        if self._profiles_collection:
            results = self._profiles_collection.get(include=["documents", "metadatas"])
            for i, doc_id in enumerate(results["ids"]):
                data["profiles"].append({
                    "id": doc_id,
                    "metadata": results["metadatas"][i],
                    "content": results["documents"][i],
                })
        
        output_file = Path(output_path)
        output_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        
        return str(output_file)
    
    def clear_all(self) -> bool:
        """Clear all data (use with caution)."""
        try:
            if self._client:
                self._client.delete_collection(self.COLLECTION_ESSAYS)
                self._client.delete_collection(self.COLLECTION_STATEMENTS)
                self._client.delete_collection(self.COLLECTION_PROFILES)
                self._init_chromadb()
            
            self._memory_essays.clear()
            self._memory_statements.clear()
            self._memory_profiles.clear()
            
            return True
        except Exception as e:
            logger.error(f"Failed to clear data: {e}")
            return False


def get_local_rag_store(persist_dir: str = "data/scholarship_rag") -> LocalRAGStore:
    """Get or create local RAG store instance."""
    return LocalRAGStore(persist_dir=persist_dir)
