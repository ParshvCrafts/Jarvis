"""
Vector Store Memory Module for JARVIS.

Provides long-term semantic memory using ChromaDB or LanceDB
for efficient similarity search.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available")


class VectorMemory:
    """
    Long-term semantic memory using vector embeddings.
    
    Features:
    - Semantic similarity search
    - Automatic embedding generation
    - Metadata filtering
    - Memory consolidation
    """
    
    def __init__(
        self,
        persist_directory: Path | str,
        collection_name: str = "jarvis_memory",
        embedding_model: str = "all-MiniLM-L6-v2",
        max_results: int = 5,
    ):
        """
        Initialize vector memory.
        
        Args:
            persist_directory: Directory for persistent storage.
            collection_name: Name of the collection.
            embedding_model: Sentence transformer model name.
            max_results: Default number of results for queries.
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.max_results = max_results
        
        self._client = None
        self._collection = None
        self._embedding_model = None
    
    @property
    def is_available(self) -> bool:
        """Check if vector memory is available."""
        return CHROMADB_AVAILABLE and SENTENCE_TRANSFORMERS_AVAILABLE
    
    def _get_client(self):
        """Get or create ChromaDB client."""
        if self._client is None and CHROMADB_AVAILABLE:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client
    
    def _get_collection(self):
        """Get or create the collection."""
        if self._collection is None:
            client = self._get_client()
            if client:
                self._collection = client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
        return self._collection
    
    def _get_embedding_model(self):
        """Get or create the embedding model."""
        if self._embedding_model is None and SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self._embedding_model = SentenceTransformer(self.embedding_model_name)
        return self._embedding_model
    
    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        model = self._get_embedding_model()
        if model is None:
            return []
        
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add a memory to the vector store.
        
        Args:
            content: Text content to store.
            metadata: Optional metadata.
            memory_id: Optional custom ID.
            
        Returns:
            Memory ID if successful.
        """
        if not self.is_available:
            logger.warning("Vector memory not available")
            return None
        
        collection = self._get_collection()
        if collection is None:
            return None
        
        if memory_id is None:
            memory_id = str(uuid.uuid4())
        
        # Prepare metadata
        meta = metadata or {}
        meta["timestamp"] = datetime.now().isoformat()
        meta["content_length"] = len(content)
        
        # Convert non-string metadata values to strings for ChromaDB
        meta = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v 
                for k, v in meta.items()}
        
        try:
            # Generate embedding
            embeddings = self._embed([content])
            
            if not embeddings:
                return None
            
            collection.add(
                ids=[memory_id],
                embeddings=embeddings,
                documents=[content],
                metadatas=[meta],
            )
            
            logger.debug(f"Added memory: {memory_id[:8]}...")
            return memory_id
        
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return None
    
    def add_batch(
        self,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        Add multiple memories in batch.
        
        Args:
            contents: List of text contents.
            metadatas: Optional list of metadata dicts.
            
        Returns:
            List of memory IDs.
        """
        if not self.is_available:
            return []
        
        collection = self._get_collection()
        if collection is None:
            return []
        
        ids = [str(uuid.uuid4()) for _ in contents]
        
        # Prepare metadatas
        if metadatas is None:
            metadatas = [{} for _ in contents]
        
        for i, meta in enumerate(metadatas):
            meta["timestamp"] = datetime.now().isoformat()
            meta["content_length"] = len(contents[i])
            metadatas[i] = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v 
                           for k, v in meta.items()}
        
        try:
            embeddings = self._embed(contents)
            
            if not embeddings:
                return []
            
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas,
            )
            
            logger.debug(f"Added {len(ids)} memories in batch")
            return ids
        
        except Exception as e:
            logger.error(f"Failed to add batch: {e}")
            return []
    
    def search(
        self,
        query: str,
        n_results: Optional[int] = None,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories.
        
        Args:
            query: Search query text.
            n_results: Number of results to return.
            where: Metadata filter.
            where_document: Document content filter.
            
        Returns:
            List of matching memories with scores.
        """
        if not self.is_available:
            return []
        
        collection = self._get_collection()
        if collection is None:
            return []
        
        if n_results is None:
            n_results = self.max_results
        
        try:
            # Generate query embedding
            query_embedding = self._embed([query])
            
            if not query_embedding:
                return []
            
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"],
            )
            
            # Format results
            memories = []
            if results["ids"] and results["ids"][0]:
                for i, memory_id in enumerate(results["ids"][0]):
                    memories.append({
                        "id": memory_id,
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                        "similarity": 1 - results["distances"][0][i] if results["distances"] else 1,
                    })
            
            return memories
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory by ID."""
        if not self.is_available:
            return None
        
        collection = self._get_collection()
        if collection is None:
            return None
        
        try:
            result = collection.get(
                ids=[memory_id],
                include=["documents", "metadatas"],
            )
            
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "content": result["documents"][0] if result["documents"] else "",
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                }
            return None
        
        except Exception as e:
            logger.error(f"Failed to get memory: {e}")
            return None
    
    def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update a memory.
        
        Args:
            memory_id: ID of memory to update.
            content: New content (optional).
            metadata: New metadata (optional).
            
        Returns:
            True if successful.
        """
        if not self.is_available:
            return False
        
        collection = self._get_collection()
        if collection is None:
            return False
        
        try:
            update_kwargs = {"ids": [memory_id]}
            
            if content is not None:
                embeddings = self._embed([content])
                if embeddings:
                    update_kwargs["embeddings"] = embeddings
                    update_kwargs["documents"] = [content]
            
            if metadata is not None:
                metadata["updated_at"] = datetime.now().isoformat()
                metadata = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v 
                           for k, v in metadata.items()}
                update_kwargs["metadatas"] = [metadata]
            
            collection.update(**update_kwargs)
            logger.debug(f"Updated memory: {memory_id[:8]}...")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return False
    
    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        if not self.is_available:
            return False
        
        collection = self._get_collection()
        if collection is None:
            return False
        
        try:
            collection.delete(ids=[memory_id])
            logger.debug(f"Deleted memory: {memory_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False
    
    def delete_where(self, where: Dict[str, Any]) -> int:
        """Delete memories matching a filter."""
        if not self.is_available:
            return 0
        
        collection = self._get_collection()
        if collection is None:
            return 0
        
        try:
            # Get matching IDs first
            results = collection.get(where=where, include=[])
            
            if results["ids"]:
                collection.delete(ids=results["ids"])
                logger.debug(f"Deleted {len(results['ids'])} memories")
                return len(results["ids"])
            return 0
        
        except Exception as e:
            logger.error(f"Failed to delete memories: {e}")
            return 0
    
    def count(self) -> int:
        """Get total number of memories."""
        if not self.is_available:
            return 0
        
        collection = self._get_collection()
        if collection is None:
            return 0
        
        return collection.count()
    
    def clear(self) -> bool:
        """Clear all memories."""
        if not self.is_available:
            return False
        
        client = self._get_client()
        if client is None:
            return False
        
        try:
            client.delete_collection(self.collection_name)
            self._collection = None
            logger.info("Cleared all memories")
            return True
        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")
            return False


class MemoryConsolidator:
    """
    Consolidates and summarizes old memories.
    
    Periodically processes old memories to:
    - Summarize related memories
    - Remove redundant information
    - Maintain memory quality
    """
    
    def __init__(
        self,
        vector_memory: VectorMemory,
        llm_manager: Any,
        consolidation_threshold: int = 100,
    ):
        """
        Initialize memory consolidator.
        
        Args:
            vector_memory: Vector memory instance.
            llm_manager: LLM manager for summarization.
            consolidation_threshold: Number of memories before consolidation.
        """
        self.vector_memory = vector_memory
        self.llm_manager = llm_manager
        self.consolidation_threshold = consolidation_threshold
    
    def should_consolidate(self) -> bool:
        """Check if consolidation is needed."""
        return self.vector_memory.count() >= self.consolidation_threshold
    
    def consolidate(self, topic: Optional[str] = None) -> int:
        """
        Consolidate memories.
        
        Args:
            topic: Optional topic to focus consolidation on.
            
        Returns:
            Number of memories consolidated.
        """
        if not self.vector_memory.is_available:
            return 0
        
        # Find similar memories to consolidate
        if topic:
            memories = self.vector_memory.search(topic, n_results=20)
        else:
            # Get oldest memories
            # Note: This is simplified - in production, use proper timestamp filtering
            memories = self.vector_memory.search("", n_results=20)
        
        if len(memories) < 3:
            return 0
        
        # Group highly similar memories
        groups = self._group_similar(memories)
        
        consolidated = 0
        for group in groups:
            if len(group) >= 2:
                self._consolidate_group(group)
                consolidated += len(group) - 1
        
        return consolidated
    
    def _group_similar(
        self,
        memories: List[Dict[str, Any]],
        similarity_threshold: float = 0.8,
    ) -> List[List[Dict[str, Any]]]:
        """Group similar memories together."""
        groups = []
        used = set()
        
        for i, mem in enumerate(memories):
            if mem["id"] in used:
                continue
            
            group = [mem]
            used.add(mem["id"])
            
            for j, other in enumerate(memories[i+1:], i+1):
                if other["id"] in used:
                    continue
                
                if other.get("similarity", 0) >= similarity_threshold:
                    group.append(other)
                    used.add(other["id"])
            
            if group:
                groups.append(group)
        
        return groups
    
    def _consolidate_group(self, group: List[Dict[str, Any]]) -> None:
        """Consolidate a group of similar memories."""
        if len(group) < 2:
            return
        
        # Combine contents
        contents = [m["content"] for m in group]
        combined = "\n\n".join(contents)
        
        # Generate summary
        try:
            from ..core.llm import Message
            
            prompt = f"""Consolidate these related memories into a single, comprehensive summary:

{combined}

Consolidated summary:"""
            
            response = self.llm_manager.generate([
                Message(role="user", content=prompt)
            ])
            
            summary = response.content.strip()
            
            # Add consolidated memory
            self.vector_memory.add(
                content=summary,
                metadata={
                    "type": "consolidated",
                    "source_count": len(group),
                    "source_ids": json.dumps([m["id"] for m in group]),
                },
            )
            
            # Delete original memories
            for mem in group:
                self.vector_memory.delete(mem["id"])
            
            logger.debug(f"Consolidated {len(group)} memories")
        
        except Exception as e:
            logger.error(f"Failed to consolidate group: {e}")
