"""
Learning Path Generator for JARVIS.

Custom skill development roadmaps:
- Generate learning paths for topics
- Track progress through paths
- Suggest resources
- Pre-defined paths for DS/ML topics
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class PathStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"


class ItemStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class PathItem:
    id: Optional[int] = None
    path_id: int = 0
    name: str = ""
    description: str = ""
    resource_url: str = ""
    resource_type: str = "article"  # article, video, course, project, book
    status: ItemStatus = ItemStatus.PENDING
    order: int = 0
    estimated_hours: float = 1.0
    completed_at: Optional[datetime] = None
    notes: str = ""
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PathItem":
        return cls(
            id=row["id"],
            path_id=row["path_id"],
            name=row["name"],
            description=row["description"] or "",
            resource_url=row["resource_url"] or "",
            resource_type=row["resource_type"] or "article",
            status=ItemStatus(row["status"]) if row["status"] else ItemStatus.PENDING,
            order=row["item_order"] or 0,
            estimated_hours=row["estimated_hours"] or 1.0,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            notes=row["notes"] or "",
        )


@dataclass
class LearningPath:
    id: Optional[int] = None
    name: str = ""
    goal: str = ""
    description: str = ""
    status: PathStatus = PathStatus.NOT_STARTED
    items: List[PathItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def progress(self) -> float:
        if not self.items:
            return 0.0
        completed = sum(1 for item in self.items if item.status == ItemStatus.COMPLETED)
        return (completed / len(self.items)) * 100
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "LearningPath":
        return cls(
            id=row["id"],
            name=row["name"],
            goal=row["goal"] or "",
            description=row["description"] or "",
            status=PathStatus(row["status"]) if row["status"] else PathStatus.NOT_STARTED,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )


class LearningPathGenerator:
    """
    Learning path generation and tracking system.
    
    Features:
    - Pre-defined paths for DS/ML topics
    - Custom path creation
    - Progress tracking
    - Resource suggestions
    """
    
    # Pre-defined learning paths
    DEFAULT_PATHS = {
        "machine_learning": {
            "name": "Machine Learning Fundamentals",
            "goal": "Master core ML concepts and algorithms",
            "description": "A comprehensive path covering supervised, unsupervised, and evaluation techniques.",
            "items": [
                {"name": "Python for Data Science", "type": "course", "hours": 10, "desc": "NumPy, Pandas, Matplotlib basics"},
                {"name": "Statistics Fundamentals", "type": "course", "hours": 8, "desc": "Probability, distributions, hypothesis testing"},
                {"name": "Linear Regression", "type": "article", "hours": 3, "desc": "Simple and multiple linear regression"},
                {"name": "Logistic Regression", "type": "article", "hours": 3, "desc": "Binary and multiclass classification"},
                {"name": "Decision Trees", "type": "video", "hours": 2, "desc": "Tree-based models and splitting criteria"},
                {"name": "Random Forests", "type": "article", "hours": 2, "desc": "Ensemble methods and bagging"},
                {"name": "Gradient Boosting", "type": "article", "hours": 3, "desc": "XGBoost, LightGBM, CatBoost"},
                {"name": "SVM", "type": "article", "hours": 2, "desc": "Support Vector Machines and kernels"},
                {"name": "Clustering", "type": "video", "hours": 2, "desc": "K-means, hierarchical, DBSCAN"},
                {"name": "Dimensionality Reduction", "type": "article", "hours": 2, "desc": "PCA, t-SNE, UMAP"},
                {"name": "Model Evaluation", "type": "article", "hours": 3, "desc": "Cross-validation, metrics, bias-variance"},
                {"name": "ML Project", "type": "project", "hours": 15, "desc": "End-to-end ML project on real dataset"},
            ]
        },
        "deep_learning": {
            "name": "Deep Learning",
            "goal": "Understand neural networks and deep learning",
            "description": "From basic neural networks to modern architectures.",
            "items": [
                {"name": "Neural Network Basics", "type": "course", "hours": 5, "desc": "Perceptrons, activation functions, backprop"},
                {"name": "PyTorch Fundamentals", "type": "course", "hours": 8, "desc": "Tensors, autograd, nn.Module"},
                {"name": "CNNs", "type": "video", "hours": 4, "desc": "Convolutional neural networks for images"},
                {"name": "RNNs and LSTMs", "type": "article", "hours": 3, "desc": "Sequence modeling"},
                {"name": "Attention Mechanism", "type": "article", "hours": 3, "desc": "Attention and self-attention"},
                {"name": "Transformers", "type": "course", "hours": 6, "desc": "Transformer architecture deep dive"},
                {"name": "Transfer Learning", "type": "article", "hours": 2, "desc": "Fine-tuning pretrained models"},
                {"name": "Regularization", "type": "article", "hours": 2, "desc": "Dropout, batch norm, weight decay"},
                {"name": "Optimization", "type": "article", "hours": 2, "desc": "SGD, Adam, learning rate schedules"},
                {"name": "DL Project", "type": "project", "hours": 20, "desc": "Build and train a deep learning model"},
            ]
        },
        "nlp": {
            "name": "Natural Language Processing",
            "goal": "Master NLP techniques and models",
            "description": "From text preprocessing to modern language models.",
            "items": [
                {"name": "Text Preprocessing", "type": "article", "hours": 2, "desc": "Tokenization, stemming, lemmatization"},
                {"name": "Word Embeddings", "type": "video", "hours": 3, "desc": "Word2Vec, GloVe, FastText"},
                {"name": "Text Classification", "type": "article", "hours": 3, "desc": "Sentiment analysis, topic classification"},
                {"name": "Named Entity Recognition", "type": "article", "hours": 2, "desc": "NER with spaCy and transformers"},
                {"name": "Sequence to Sequence", "type": "video", "hours": 3, "desc": "Encoder-decoder models"},
                {"name": "BERT", "type": "course", "hours": 5, "desc": "Understanding and using BERT"},
                {"name": "GPT and Language Models", "type": "article", "hours": 4, "desc": "Autoregressive language models"},
                {"name": "Hugging Face Transformers", "type": "course", "hours": 6, "desc": "Using the transformers library"},
                {"name": "NLP Project", "type": "project", "hours": 15, "desc": "Build an NLP application"},
            ]
        },
        "computer_vision": {
            "name": "Computer Vision",
            "goal": "Master image and video analysis",
            "description": "From basic image processing to modern CV models.",
            "items": [
                {"name": "Image Basics", "type": "article", "hours": 2, "desc": "Pixels, channels, color spaces"},
                {"name": "OpenCV Fundamentals", "type": "course", "hours": 5, "desc": "Image manipulation with OpenCV"},
                {"name": "Image Classification", "type": "video", "hours": 3, "desc": "CNN-based classification"},
                {"name": "Object Detection", "type": "course", "hours": 5, "desc": "YOLO, Faster R-CNN"},
                {"name": "Image Segmentation", "type": "article", "hours": 3, "desc": "Semantic and instance segmentation"},
                {"name": "Vision Transformers", "type": "article", "hours": 3, "desc": "ViT and modern architectures"},
                {"name": "Data Augmentation", "type": "article", "hours": 2, "desc": "Augmentation techniques"},
                {"name": "CV Project", "type": "project", "hours": 15, "desc": "Build a computer vision application"},
            ]
        },
        "data_engineering": {
            "name": "Data Engineering",
            "goal": "Build data pipelines and infrastructure",
            "description": "From SQL to distributed systems.",
            "items": [
                {"name": "SQL Mastery", "type": "course", "hours": 8, "desc": "Advanced SQL queries and optimization"},
                {"name": "Python Data Processing", "type": "article", "hours": 3, "desc": "Pandas, Dask for large data"},
                {"name": "Data Modeling", "type": "video", "hours": 3, "desc": "Schema design, normalization"},
                {"name": "ETL Pipelines", "type": "course", "hours": 5, "desc": "Extract, Transform, Load processes"},
                {"name": "Apache Spark", "type": "course", "hours": 8, "desc": "Distributed data processing"},
                {"name": "Airflow", "type": "article", "hours": 4, "desc": "Workflow orchestration"},
                {"name": "Data Warehousing", "type": "video", "hours": 3, "desc": "Warehouse concepts and tools"},
                {"name": "DE Project", "type": "project", "hours": 15, "desc": "Build a data pipeline"},
            ]
        },
        "mlops": {
            "name": "MLOps",
            "goal": "Deploy and maintain ML systems",
            "description": "From model training to production deployment.",
            "items": [
                {"name": "Git for ML", "type": "article", "hours": 2, "desc": "Version control best practices"},
                {"name": "Docker Basics", "type": "course", "hours": 4, "desc": "Containerization for ML"},
                {"name": "Model Versioning", "type": "article", "hours": 2, "desc": "DVC, MLflow model registry"},
                {"name": "Experiment Tracking", "type": "video", "hours": 2, "desc": "MLflow, Weights & Biases"},
                {"name": "Model Serving", "type": "course", "hours": 4, "desc": "FastAPI, Flask for ML APIs"},
                {"name": "CI/CD for ML", "type": "article", "hours": 3, "desc": "Automated testing and deployment"},
                {"name": "Monitoring", "type": "article", "hours": 2, "desc": "Model monitoring and drift detection"},
                {"name": "Kubernetes Basics", "type": "course", "hours": 5, "desc": "Container orchestration"},
                {"name": "MLOps Project", "type": "project", "hours": 15, "desc": "Deploy an ML model to production"},
            ]
        },
    }
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "learning_paths.db"
        
        self._init_db()
        logger.info("Learning Path Generator initialized")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paths (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    goal TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'not_started',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS path_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    resource_url TEXT,
                    resource_type TEXT DEFAULT 'article',
                    status TEXT DEFAULT 'pending',
                    item_order INTEGER DEFAULT 0,
                    estimated_hours REAL DEFAULT 1.0,
                    completed_at TEXT,
                    notes TEXT,
                    FOREIGN KEY (path_id) REFERENCES paths(id)
                )
            """)
            conn.commit()
    
    def create_path(
        self,
        name: str,
        goal: str = "",
        description: str = "",
        template: Optional[str] = None,
    ) -> LearningPath:
        """Create a new learning path."""
        # Check if using a template
        if template and template.lower().replace(" ", "_") in self.DEFAULT_PATHS:
            template_data = self.DEFAULT_PATHS[template.lower().replace(" ", "_")]
            name = template_data["name"]
            goal = template_data["goal"]
            description = template_data["description"]
        
        path = LearningPath(
            name=name,
            goal=goal,
            description=description,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO paths (name, goal, description, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (path.name, path.goal, path.description, path.status.value, path.created_at.isoformat()))
            path.id = cursor.lastrowid
            
            # Add template items if using template
            if template and template.lower().replace(" ", "_") in self.DEFAULT_PATHS:
                template_data = self.DEFAULT_PATHS[template.lower().replace(" ", "_")]
                for i, item_data in enumerate(template_data["items"]):
                    conn.execute("""
                        INSERT INTO path_items (path_id, name, description, resource_type, item_order, estimated_hours)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (path.id, item_data["name"], item_data["desc"], item_data["type"], i, item_data["hours"]))
            
            conn.commit()
        
        logger.info(f"Created learning path: {name}")
        return path
    
    def get_path(self, path_id: int) -> Optional[LearningPath]:
        """Get a learning path with its items."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            row = conn.execute("SELECT * FROM paths WHERE id = ?", (path_id,)).fetchone()
            if not row:
                return None
            
            path = LearningPath.from_row(row)
            
            items = conn.execute(
                "SELECT * FROM path_items WHERE path_id = ? ORDER BY item_order",
                (path_id,)
            ).fetchall()
            
            path.items = [PathItem.from_row(item) for item in items]
        
        return path
    
    def get_path_by_name(self, name: str) -> Optional[LearningPath]:
        """Get a learning path by name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            row = conn.execute(
                "SELECT * FROM paths WHERE LOWER(name) LIKE ? LIMIT 1",
                (f"%{name.lower()}%",)
            ).fetchone()
            
            if not row:
                return None
            
            path = LearningPath.from_row(row)
            
            items = conn.execute(
                "SELECT * FROM path_items WHERE path_id = ? ORDER BY item_order",
                (path.id,)
            ).fetchall()
            
            path.items = [PathItem.from_row(item) for item in items]
        
        return path
    
    def get_all_paths(self) -> List[LearningPath]:
        """Get all learning paths."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM paths ORDER BY created_at DESC"
            ).fetchall()
        
        paths = []
        for row in rows:
            path = LearningPath.from_row(row)
            path = self.get_path(path.id)  # Load items
            if path:
                paths.append(path)
        
        return paths
    
    def complete_item(self, path_name: str, item_name: str, notes: str = "") -> str:
        """Mark a learning path item as completed."""
        path = self.get_path_by_name(path_name)
        if not path:
            return f"No learning path found matching '{path_name}'."
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                UPDATE path_items 
                SET status = ?, completed_at = ?, notes = ?
                WHERE path_id = ? AND LOWER(name) LIKE ?
            """, (
                ItemStatus.COMPLETED.value,
                datetime.now().isoformat(),
                notes,
                path.id,
                f"%{item_name.lower()}%"
            ))
            
            if result.rowcount == 0:
                return f"No item found matching '{item_name}' in {path.name}."
            
            # Update path status if needed
            if path.status == PathStatus.NOT_STARTED:
                conn.execute(
                    "UPDATE paths SET status = ?, started_at = ? WHERE id = ?",
                    (PathStatus.IN_PROGRESS.value, datetime.now().isoformat(), path.id)
                )
            
            # Check if all items completed
            remaining = conn.execute("""
                SELECT COUNT(*) FROM path_items 
                WHERE path_id = ? AND status != 'completed' AND status != 'skipped'
            """, (path.id,)).fetchone()[0]
            
            if remaining == 0:
                conn.execute(
                    "UPDATE paths SET status = ?, completed_at = ? WHERE id = ?",
                    (PathStatus.COMPLETED.value, datetime.now().isoformat(), path.id)
                )
            
            conn.commit()
        
        return f"✅ Completed '{item_name}' in {path.name}!"
    
    def get_next_item(self, path_name: str) -> str:
        """Get the next item to work on in a path."""
        path = self.get_path_by_name(path_name)
        if not path:
            return f"No learning path found matching '{path_name}'."
        
        for item in path.items:
            if item.status in [ItemStatus.PENDING, ItemStatus.IN_PROGRESS]:
                type_emoji = {
                    "article": "📄",
                    "video": "🎥",
                    "course": "📚",
                    "project": "💻",
                    "book": "📖",
                }
                emoji = type_emoji.get(item.resource_type, "📌")
                
                return f"""📍 **Next in {path.name}:**

{emoji} **{item.name}**
{item.description}

⏱️ Estimated: {item.estimated_hours} hours
Type: {item.resource_type.title()}"""
        
        return f"🎉 You've completed all items in {path.name}!"
    
    def add_item(
        self,
        path_name: str,
        item_name: str,
        description: str = "",
        resource_url: str = "",
        resource_type: str = "article",
        hours: float = 1.0,
    ) -> str:
        """Add an item to a learning path."""
        path = self.get_path_by_name(path_name)
        if not path:
            return f"No learning path found matching '{path_name}'."
        
        with sqlite3.connect(self.db_path) as conn:
            max_order = conn.execute(
                "SELECT MAX(item_order) FROM path_items WHERE path_id = ?",
                (path.id,)
            ).fetchone()[0] or 0
            
            conn.execute("""
                INSERT INTO path_items (path_id, name, description, resource_url, resource_type, item_order, estimated_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (path.id, item_name, description, resource_url, resource_type, max_order + 1, hours))
            conn.commit()
        
        return f"✅ Added '{item_name}' to {path.name}"
    
    def format_path(self, path: LearningPath) -> str:
        """Format a learning path for display."""
        status_emoji = {
            PathStatus.NOT_STARTED: "⬜",
            PathStatus.IN_PROGRESS: "🔄",
            PathStatus.COMPLETED: "✅",
            PathStatus.PAUSED: "⏸️",
        }
        
        item_status_emoji = {
            ItemStatus.PENDING: "⬜",
            ItemStatus.IN_PROGRESS: "🔄",
            ItemStatus.COMPLETED: "✅",
            ItemStatus.SKIPPED: "⏭️",
        }
        
        lines = [
            f"📚 **{path.name}** {status_emoji.get(path.status, '')}",
            f"Goal: {path.goal}",
            f"Progress: {path.progress:.0f}%\n",
            "**Items:**",
        ]
        
        for item in path.items:
            emoji = item_status_emoji.get(item.status, "⬜")
            lines.append(f"  {emoji} {item.name} ({item.estimated_hours}h)")
        
        total_hours = sum(item.estimated_hours for item in path.items)
        completed_hours = sum(item.estimated_hours for item in path.items if item.status == ItemStatus.COMPLETED)
        
        lines.append(f"\n⏱️ {completed_hours:.0f}/{total_hours:.0f} hours completed")
        
        return "\n".join(lines)
    
    def list_paths(self) -> str:
        """List all learning paths."""
        paths = self.get_all_paths()
        
        if not paths:
            lines = ["📚 **Available Learning Path Templates:**\n"]
            for key, template in self.DEFAULT_PATHS.items():
                lines.append(f"  • **{template['name']}**")
                lines.append(f"    {template['goal']}")
            lines.append("\nSay 'create learning path for [topic]' to start one!")
            return "\n".join(lines)
        
        lines = ["📚 **Your Learning Paths**\n"]
        
        for path in paths:
            status_emoji = {"not_started": "⬜", "in_progress": "🔄", "completed": "✅", "paused": "⏸️"}
            emoji = status_emoji.get(path.status.value, "⬜")
            lines.append(f"{emoji} **{path.name}** - {path.progress:.0f}%")
        
        return "\n".join(lines)
    
    def get_available_templates(self) -> List[str]:
        """Get list of available template names."""
        return list(self.DEFAULT_PATHS.keys())
