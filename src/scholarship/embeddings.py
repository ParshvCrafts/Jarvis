"""
Embedding Generation for JARVIS Scholarship Module.

Supports multiple embedding providers:
- Sentence Transformers (local, free)
- OpenAI Embeddings (paid)
- Cohere Embed (free tier)
- Voyage AI (free tier)
"""

import os
from typing import List, Optional, Union
from enum import Enum

from loguru import logger

# Try importing embedding libraries
SENTENCE_TRANSFORMERS_AVAILABLE = False
OPENAI_AVAILABLE = False
COHERE_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.debug("sentence-transformers not installed")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    logger.debug("openai not installed")

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    logger.debug("cohere not installed")


class EmbeddingProvider(Enum):
    """Available embedding providers."""
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"
    COHERE = "cohere"
    VOYAGE = "voyage"


class EmbeddingGenerator:
    """
    Generate embeddings for text using various providers.
    
    Default: Sentence Transformers (local, free, no API key needed)
    """
    
    # Model configurations
    MODELS = {
        EmbeddingProvider.SENTENCE_TRANSFORMERS: "all-MiniLM-L6-v2",  # 384 dimensions
        EmbeddingProvider.OPENAI: "text-embedding-3-small",  # 1536 dimensions
        EmbeddingProvider.COHERE: "embed-english-v3.0",  # 1024 dimensions
    }
    
    DIMENSIONS = {
        EmbeddingProvider.SENTENCE_TRANSFORMERS: 384,
        EmbeddingProvider.OPENAI: 1536,
        EmbeddingProvider.COHERE: 1024,
    }
    
    def __init__(
        self,
        provider: EmbeddingProvider = EmbeddingProvider.SENTENCE_TRANSFORMERS,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize embedding generator.
        
        Args:
            provider: Which embedding provider to use
            model_name: Override default model name
            api_key: API key for cloud providers
        """
        self.provider = provider
        self.model_name = model_name or self.MODELS.get(provider)
        self.api_key = api_key
        self.dimensions = self.DIMENSIONS.get(provider, 384)
        
        self._model = None
        self._client = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialize the embedding model/client."""
        if self.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                )
            logger.info(f"Loading Sentence Transformer model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            self.dimensions = self._model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Dimensions: {self.dimensions}")
        
        elif self.provider == EmbeddingProvider.OPENAI:
            if not OPENAI_AVAILABLE:
                raise ImportError("openai not installed. Run: pip install openai")
            api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key required")
            self._client = openai.OpenAI(api_key=api_key)
        
        elif self.provider == EmbeddingProvider.COHERE:
            if not COHERE_AVAILABLE:
                raise ImportError("cohere not installed. Run: pip install cohere")
            api_key = self.api_key or os.getenv("COHERE_API_KEY")
            if not api_key:
                raise ValueError("Cohere API key required")
            self._client = cohere.Client(api_key)
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats (embedding vector)
        """
        if self.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        
        elif self.provider == EmbeddingProvider.OPENAI:
            response = self._client.embeddings.create(
                model=self.model_name,
                input=text,
            )
            return response.data[0].embedding
        
        elif self.provider == EmbeddingProvider.COHERE:
            response = self._client.embed(
                texts=[text],
                model=self.model_name,
                input_type="search_document",
            )
            return response.embeddings[0]
        
        raise ValueError(f"Unsupported provider: {self.provider}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        if self.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        
        elif self.provider == EmbeddingProvider.OPENAI:
            response = self._client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
            return [item.embedding for item in response.data]
        
        elif self.provider == EmbeddingProvider.COHERE:
            response = self._client.embed(
                texts=texts,
                model=self.model_name,
                input_type="search_document",
            )
            return response.embeddings
        
        raise ValueError(f"Unsupported provider: {self.provider}")
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Some providers have different modes for queries vs documents.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector
        """
        if self.provider == EmbeddingProvider.COHERE:
            response = self._client.embed(
                texts=[query],
                model=self.model_name,
                input_type="search_query",
            )
            return response.embeddings[0]
        
        # For other providers, same as regular embed
        return self.embed(query)
    
    def similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Similarity score (0-1)
        """
        import math
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = math.sqrt(sum(a * a for a in embedding1))
        norm2 = math.sqrt(sum(b * b for b in embedding2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5,
    ) -> List[tuple]:
        """
        Find most similar embeddings to a query.
        
        Args:
            query_embedding: Query embedding
            candidate_embeddings: List of candidate embeddings
            top_k: Number of results to return
            
        Returns:
            List of (index, similarity_score) tuples
        """
        similarities = [
            (i, self.similarity(query_embedding, emb))
            for i, emb in enumerate(candidate_embeddings)
        ]
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]


def get_default_embedder() -> EmbeddingGenerator:
    """
    Get the default embedding generator.
    
    Tries providers in order of preference:
    1. Sentence Transformers (free, local)
    2. Cohere (free tier)
    3. OpenAI (paid)
    """
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        return EmbeddingGenerator(EmbeddingProvider.SENTENCE_TRANSFORMERS)
    
    if COHERE_AVAILABLE and os.getenv("COHERE_API_KEY"):
        return EmbeddingGenerator(EmbeddingProvider.COHERE)
    
    if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        return EmbeddingGenerator(EmbeddingProvider.OPENAI)
    
    raise ImportError(
        "No embedding provider available. Install sentence-transformers: "
        "pip install sentence-transformers"
    )
