"""
Code Snippet Library for JARVIS.

Save and retrieve reusable code snippets:
- Categorized by language and topic
- Searchable by tags
- Pre-loaded DS/ML snippets
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class CodeSnippet:
    """A reusable code snippet."""
    id: Optional[int] = None
    name: str = ""
    language: str = "python"
    category: str = "general"
    code: str = ""
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    use_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"[{self.language}] {self.name}"


class SnippetLibrary:
    """
    Code snippet storage and retrieval.
    
    Usage:
        library = SnippetLibrary()
        library.save("train_test_split", code, language="python", category="ml")
        snippets = library.search("pandas")
    """
    
    # Pre-loaded DS/ML snippets
    DEFAULT_SNIPPETS = [
        # Data Loading
        CodeSnippet(
            name="pandas_read_csv",
            language="python",
            category="data_loading",
            code='''import pandas as pd

# Read CSV with common options
df = pd.read_csv('data.csv', 
    encoding='utf-8',
    parse_dates=['date_column'],
    na_values=['NA', 'N/A', ''],
    dtype={'id': str}
)
print(f"Shape: {df.shape}")
df.head()''',
            description="Read CSV file with pandas and common options",
            tags=["pandas", "csv", "data", "loading"],
        ),
        CodeSnippet(
            name="numpy_basics",
            language="python",
            category="data_loading",
            code='''import numpy as np

# Create arrays
arr = np.array([1, 2, 3, 4, 5])
zeros = np.zeros((3, 4))
ones = np.ones((2, 3))
range_arr = np.arange(0, 10, 2)
linspace = np.linspace(0, 1, 5)

# Random
random_arr = np.random.rand(3, 3)
random_int = np.random.randint(0, 100, size=(5,))''',
            description="NumPy array creation basics",
            tags=["numpy", "array", "basics"],
        ),
        
        # ML Basics
        CodeSnippet(
            name="train_test_split",
            language="python",
            category="ml",
            code='''from sklearn.model_selection import train_test_split

# Split data into train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size=0.2, 
    random_state=42,
    stratify=y  # For classification
)
print(f"Train: {X_train.shape}, Test: {X_test.shape}")''',
            description="Split data into training and test sets",
            tags=["sklearn", "train", "test", "split", "ml"],
        ),
        CodeSnippet(
            name="standard_scaler",
            language="python",
            category="ml",
            code='''from sklearn.preprocessing import StandardScaler

# Standardize features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)  # Use same scaler!''',
            description="Standardize features using StandardScaler",
            tags=["sklearn", "scaler", "preprocessing", "normalize"],
        ),
        CodeSnippet(
            name="logistic_regression",
            language="python",
            category="ml",
            code='''from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

# Train logistic regression
model = LogisticRegression(random_state=42, max_iter=1000)
model.fit(X_train, y_train)

# Predict and evaluate
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")
print(classification_report(y_test, y_pred))''',
            description="Train and evaluate logistic regression",
            tags=["sklearn", "logistic", "regression", "classification"],
        ),
        CodeSnippet(
            name="random_forest",
            language="python",
            category="ml",
            code='''from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# Train random forest
rf = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train)

# Feature importance
importance = pd.DataFrame({
    'feature': feature_names,
    'importance': rf.feature_importances_
}).sort_values('importance', ascending=False)''',
            description="Train random forest with feature importance",
            tags=["sklearn", "random forest", "classification", "feature importance"],
        ),
        CodeSnippet(
            name="confusion_matrix",
            language="python",
            category="ml",
            code='''from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt

# Create confusion matrix
cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(confusion_matrix=cm)
disp.plot(cmap='Blues')
plt.title('Confusion Matrix')
plt.show()''',
            description="Plot confusion matrix",
            tags=["sklearn", "confusion matrix", "evaluation", "plot"],
        ),
        CodeSnippet(
            name="cross_validation",
            language="python",
            category="ml",
            code='''from sklearn.model_selection import cross_val_score

# K-fold cross validation
scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
print(f"CV Scores: {scores}")
print(f"Mean: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")''',
            description="K-fold cross validation",
            tags=["sklearn", "cross validation", "cv", "evaluation"],
        ),
        
        # Visualization
        CodeSnippet(
            name="matplotlib_basic",
            language="python",
            category="visualization",
            code='''import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(x, y, label='Line', color='blue', linewidth=2)
ax.scatter(x, y, label='Points', color='red', alpha=0.5)
ax.set_xlabel('X Label')
ax.set_ylabel('Y Label')
ax.set_title('Title')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()''',
            description="Basic matplotlib plot template",
            tags=["matplotlib", "plot", "visualization"],
        ),
        CodeSnippet(
            name="seaborn_heatmap",
            language="python",
            category="visualization",
            code='''import seaborn as sns
import matplotlib.pyplot as plt

# Correlation heatmap
plt.figure(figsize=(10, 8))
correlation = df.corr()
sns.heatmap(correlation, 
    annot=True, 
    cmap='coolwarm', 
    center=0,
    fmt='.2f',
    square=True
)
plt.title('Correlation Heatmap')
plt.tight_layout()
plt.show()''',
            description="Seaborn correlation heatmap",
            tags=["seaborn", "heatmap", "correlation", "visualization"],
        ),
        CodeSnippet(
            name="histogram",
            language="python",
            category="visualization",
            code='''import matplotlib.pyplot as plt
import seaborn as sns

fig, ax = plt.subplots(figsize=(10, 6))
sns.histplot(data=df, x='column', bins=30, kde=True, ax=ax)
ax.set_title('Distribution of Column')
ax.set_xlabel('Value')
ax.set_ylabel('Frequency')
plt.show()''',
            description="Histogram with KDE",
            tags=["histogram", "distribution", "seaborn", "visualization"],
        ),
        
        # Data Processing
        CodeSnippet(
            name="handle_missing",
            language="python",
            category="data_processing",
            code='''# Check missing values
print(df.isnull().sum())
print(f"\\nMissing %:\\n{df.isnull().mean() * 100}")

# Fill missing values
df['numeric_col'].fillna(df['numeric_col'].median(), inplace=True)
df['category_col'].fillna('Unknown', inplace=True)

# Or drop rows with missing values
df_clean = df.dropna(subset=['important_col'])''',
            description="Handle missing values in pandas",
            tags=["pandas", "missing", "null", "fillna", "dropna"],
        ),
        CodeSnippet(
            name="one_hot_encoding",
            language="python",
            category="data_processing",
            code='''import pandas as pd
from sklearn.preprocessing import OneHotEncoder

# Method 1: pandas get_dummies
df_encoded = pd.get_dummies(df, columns=['category_col'], drop_first=True)

# Method 2: sklearn OneHotEncoder
encoder = OneHotEncoder(sparse=False, drop='first')
encoded = encoder.fit_transform(df[['category_col']])
encoded_df = pd.DataFrame(encoded, columns=encoder.get_feature_names_out())''',
            description="One-hot encode categorical variables",
            tags=["encoding", "categorical", "one-hot", "preprocessing"],
        ),
        
        # Deep Learning
        CodeSnippet(
            name="pytorch_model",
            language="python",
            category="deep_learning",
            code='''import torch
import torch.nn as nn

class SimpleNN(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(SimpleNN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
        self.fc2 = nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x

model = SimpleNN(input_size=784, hidden_size=128, num_classes=10)''',
            description="Simple PyTorch neural network",
            tags=["pytorch", "neural network", "deep learning", "model"],
        ),
        CodeSnippet(
            name="pytorch_training_loop",
            language="python",
            category="deep_learning",
            code='''import torch.optim as optim

# Setup
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Training loop
num_epochs = 10
for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    
    for inputs, labels in train_loader:
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
    
    print(f"Epoch {epoch+1}/{num_epochs}, Loss: {running_loss/len(train_loader):.4f}")''',
            description="PyTorch training loop template",
            tags=["pytorch", "training", "deep learning", "loop"],
        ),
        
        # Common Imports
        CodeSnippet(
            name="ds_imports",
            language="python",
            category="imports",
            code='''# Data Science Imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Settings
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 100)
plt.style.use('seaborn-v0_8-whitegrid')
%matplotlib inline

# Warnings
import warnings
warnings.filterwarnings('ignore')''',
            description="Common data science imports",
            tags=["imports", "pandas", "numpy", "matplotlib", "seaborn"],
        ),
        CodeSnippet(
            name="ml_imports",
            language="python",
            category="imports",
            code='''# ML Imports
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import confusion_matrix, classification_report, roc_auc_score

# Models
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier''',
            description="Common ML imports",
            tags=["imports", "sklearn", "ml", "models"],
        ),
    ]
    
    def __init__(self, db_path: str = "data/snippets.db"):
        """
        Initialize snippet library.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS code_snippets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    language TEXT DEFAULT 'python',
                    category TEXT DEFAULT 'general',
                    code TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    use_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snippets_language 
                ON code_snippets(language)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snippets_category 
                ON code_snippets(category)
            """)
            conn.commit()
    
    def load_defaults(self) -> int:
        """Load default snippets. Returns count of snippets added."""
        count = 0
        for snippet in self.DEFAULT_SNIPPETS:
            try:
                self.save(
                    name=snippet.name,
                    code=snippet.code,
                    language=snippet.language,
                    category=snippet.category,
                    description=snippet.description,
                    tags=snippet.tags,
                )
                count += 1
            except Exception:
                pass  # Already exists
        return count
    
    def save(
        self,
        name: str,
        code: str,
        language: str = "python",
        category: str = "general",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> CodeSnippet:
        """
        Save a code snippet.
        
        Args:
            name: Snippet name
            code: The code
            language: Programming language
            category: Category (ml, visualization, etc.)
            description: Description
            tags: Search tags
            
        Returns:
            Created snippet
        """
        snippet = CodeSnippet(
            name=name.lower().replace(" ", "_"),
            language=language.lower(),
            category=category.lower(),
            code=code,
            description=description,
            tags=tags or [],
        )
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO code_snippets 
                    (name, language, category, code, description, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    snippet.name,
                    snippet.language,
                    snippet.category,
                    snippet.code,
                    snippet.description,
                    "|".join(snippet.tags),
                ))
                snippet.id = cursor.lastrowid
                conn.commit()
                logger.info(f"Saved snippet: {snippet.name}")
            except sqlite3.IntegrityError:
                # Update existing
                conn.execute("""
                    UPDATE code_snippets 
                    SET code = ?, description = ?, tags = ?
                    WHERE name = ?
                """, (snippet.code, snippet.description, "|".join(snippet.tags), snippet.name))
                conn.commit()
        
        return snippet
    
    def get(self, name: str) -> Optional[CodeSnippet]:
        """Get a snippet by name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM code_snippets WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{name}%",)
            ).fetchone()
            
            if row:
                # Increment use count
                conn.execute(
                    "UPDATE code_snippets SET use_count = use_count + 1 WHERE id = ?",
                    (row["id"],)
                )
                conn.commit()
                return self._row_to_snippet(row)
        return None
    
    def search(self, query: str, limit: int = 10) -> List[CodeSnippet]:
        """Search snippets by name, description, or tags."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM code_snippets
                WHERE LOWER(name) LIKE LOWER(?)
                   OR LOWER(description) LIKE LOWER(?)
                   OR LOWER(tags) LIKE LOWER(?)
                   OR LOWER(category) LIKE LOWER(?)
                ORDER BY use_count DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()
            
            return [self._row_to_snippet(row) for row in rows]
    
    def get_by_category(self, category: str) -> List[CodeSnippet]:
        """Get snippets by category."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM code_snippets
                WHERE LOWER(category) = LOWER(?)
                ORDER BY use_count DESC
            """, (category,)).fetchall()
            
            return [self._row_to_snippet(row) for row in rows]
    
    def get_by_language(self, language: str) -> List[CodeSnippet]:
        """Get snippets by language."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM code_snippets
                WHERE LOWER(language) = LOWER(?)
                ORDER BY use_count DESC
            """, (language,)).fetchall()
            
            return [self._row_to_snippet(row) for row in rows]
    
    def get_most_used(self, limit: int = 10) -> List[CodeSnippet]:
        """Get most frequently used snippets."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM code_snippets
                ORDER BY use_count DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [self._row_to_snippet(row) for row in rows]
    
    def get_all(self) -> List[CodeSnippet]:
        """Get all snippets."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM code_snippets ORDER BY category, name"
            ).fetchall()
            
            return [self._row_to_snippet(row) for row in rows]
    
    def delete(self, name: str) -> str:
        """Delete a snippet."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM code_snippets WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{name}%",)
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                return f"Deleted snippet: {name}"
            return f"Snippet '{name}' not found."
    
    def format_snippet(self, snippet: CodeSnippet, show_code: bool = True) -> str:
        """Format a snippet for display."""
        lines = [f"📝 **{snippet.name}** [{snippet.language}]"]
        
        if snippet.description:
            lines.append(f"   {snippet.description}")
        
        if snippet.tags:
            lines.append(f"   Tags: {', '.join(snippet.tags)}")
        
        if show_code:
            lines.append(f"\n```{snippet.language}")
            lines.append(snippet.code)
            lines.append("```")
        
        return "\n".join(lines)
    
    def format_snippets(self, snippets: List[CodeSnippet]) -> str:
        """Format multiple snippets for display (without code)."""
        if not snippets:
            return "No snippets found."
        
        lines = ["📚 Code Snippets", ""]
        
        # Group by category
        categories = {}
        for s in snippets:
            if s.category not in categories:
                categories[s.category] = []
            categories[s.category].append(s)
        
        for cat, cat_snippets in sorted(categories.items()):
            lines.append(f"**{cat.replace('_', ' ').title()}:**")
            for s in cat_snippets:
                lines.append(f"  • {s.name} - {s.description or 'No description'}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _row_to_snippet(self, row: sqlite3.Row) -> CodeSnippet:
        """Convert database row to CodeSnippet."""
        return CodeSnippet(
            id=row["id"],
            name=row["name"],
            language=row["language"],
            category=row["category"],
            code=row["code"],
            description=row["description"],
            tags=row["tags"].split("|") if row["tags"] else [],
            use_count=row["use_count"],
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
        )
