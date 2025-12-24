"""
Dataset Explorer for JARVIS.

Quick analysis of CSV/data files:
- Load and inspect datasets
- Basic statistics
- Missing value analysis
- Column information
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

# Pandas import
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None


@dataclass
class DatasetInfo:
    """Information about a dataset."""
    path: str
    rows: int
    columns: int
    memory_mb: float
    column_names: List[str]
    dtypes: Dict[str, str]
    missing_counts: Dict[str, int]
    missing_percentages: Dict[str, float]


class DatasetExplorer:
    """
    Quick dataset analysis tool.
    
    Usage:
        explorer = DatasetExplorer()
        info = explorer.load("data.csv")
        stats = explorer.describe()
        explorer.show_missing()
    """
    
    # Common data directories to search
    SEARCH_PATHS = [
        ".",
        "data",
        "datasets",
        "~/Downloads",
        "~/Documents",
        "~/Desktop",
    ]
    
    def __init__(self):
        """Initialize dataset explorer."""
        if not PANDAS_AVAILABLE:
            logger.warning("Pandas not available. Install with: pip install pandas")
        
        self.df: Optional[pd.DataFrame] = None
        self.current_path: Optional[str] = None
        self.info: Optional[DatasetInfo] = None
    
    @property
    def is_available(self) -> bool:
        """Check if pandas is available."""
        return PANDAS_AVAILABLE
    
    @property
    def is_loaded(self) -> bool:
        """Check if a dataset is loaded."""
        return self.df is not None
    
    def load(
        self,
        path: str,
        **kwargs,
    ) -> str:
        """
        Load a dataset from file.
        
        Args:
            path: Path to file (CSV, Excel, JSON, Parquet)
            **kwargs: Additional arguments for pandas read function
            
        Returns:
            Status message with basic info
        """
        if not PANDAS_AVAILABLE:
            return "Pandas is not installed. Install with: pip install pandas"
        
        # Find the file
        file_path = self._find_file(path)
        if not file_path:
            return f"File not found: {path}\nSearched in: {', '.join(self.SEARCH_PATHS)}"
        
        try:
            # Determine file type and load
            suffix = file_path.suffix.lower()
            
            if suffix == ".csv":
                self.df = pd.read_csv(file_path, **kwargs)
            elif suffix in [".xlsx", ".xls"]:
                self.df = pd.read_excel(file_path, **kwargs)
            elif suffix == ".json":
                self.df = pd.read_json(file_path, **kwargs)
            elif suffix == ".parquet":
                self.df = pd.read_parquet(file_path, **kwargs)
            elif suffix == ".tsv":
                self.df = pd.read_csv(file_path, sep="\t", **kwargs)
            else:
                # Try CSV as default
                self.df = pd.read_csv(file_path, **kwargs)
            
            self.current_path = str(file_path)
            self.info = self._get_info()
            
            logger.info(f"Loaded dataset: {file_path}")
            
            return self._format_load_summary()
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            return f"Failed to load {path}: {str(e)}"
    
    def _find_file(self, path: str) -> Optional[Path]:
        """Find a file in common locations."""
        # Check if absolute path
        p = Path(path)
        if p.is_absolute() and p.exists():
            return p
        
        # Search in common directories
        for search_dir in self.SEARCH_PATHS:
            search_path = Path(search_dir).expanduser() / path
            if search_path.exists():
                return search_path
        
        # Check current directory
        if Path(path).exists():
            return Path(path)
        
        return None
    
    def _get_info(self) -> DatasetInfo:
        """Get dataset information."""
        if self.df is None:
            return None
        
        missing_counts = self.df.isnull().sum().to_dict()
        missing_pcts = (self.df.isnull().mean() * 100).to_dict()
        
        return DatasetInfo(
            path=self.current_path,
            rows=len(self.df),
            columns=len(self.df.columns),
            memory_mb=self.df.memory_usage(deep=True).sum() / 1024 / 1024,
            column_names=list(self.df.columns),
            dtypes={col: str(dtype) for col, dtype in self.df.dtypes.items()},
            missing_counts=missing_counts,
            missing_percentages=missing_pcts,
        )
    
    def _format_load_summary(self) -> str:
        """Format load summary."""
        if not self.info:
            return "No dataset loaded."
        
        lines = [
            f"📊 Dataset Loaded: {Path(self.info.path).name}",
            "",
            f"📏 Shape: {self.info.rows:,} rows × {self.info.columns} columns",
            f"💾 Memory: {self.info.memory_mb:.2f} MB",
            "",
            "📋 Columns:",
        ]
        
        for col in self.info.column_names[:10]:
            dtype = self.info.dtypes[col]
            missing = self.info.missing_counts[col]
            missing_str = f" ({missing} missing)" if missing > 0 else ""
            lines.append(f"  • {col} [{dtype}]{missing_str}")
        
        if len(self.info.column_names) > 10:
            lines.append(f"  ... and {len(self.info.column_names) - 10} more columns")
        
        return "\n".join(lines)
    
    def describe(self, column: Optional[str] = None) -> str:
        """
        Get statistical description of the dataset.
        
        Args:
            column: Optional specific column to describe
            
        Returns:
            Formatted statistics
        """
        if not self.is_loaded:
            return "No dataset loaded. Use 'Analyze dataset [file]' first."
        
        try:
            if column:
                if column not in self.df.columns:
                    return f"Column '{column}' not found."
                
                desc = self.df[column].describe()
                lines = [f"📊 Statistics for '{column}':", ""]
                for stat, value in desc.items():
                    if isinstance(value, float):
                        lines.append(f"  {stat}: {value:.4f}")
                    else:
                        lines.append(f"  {stat}: {value}")
                return "\n".join(lines)
            
            # Full dataset description
            desc = self.df.describe(include='all')
            
            lines = ["📊 Dataset Statistics", ""]
            
            # Numeric columns
            numeric_cols = self.df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                lines.append("**Numeric Columns:**")
                for col in numeric_cols[:5]:
                    mean = self.df[col].mean()
                    std = self.df[col].std()
                    lines.append(f"  • {col}: mean={mean:.2f}, std={std:.2f}")
                if len(numeric_cols) > 5:
                    lines.append(f"  ... and {len(numeric_cols) - 5} more")
                lines.append("")
            
            # Categorical columns
            cat_cols = self.df.select_dtypes(include=['object', 'category']).columns
            if len(cat_cols) > 0:
                lines.append("**Categorical Columns:**")
                for col in cat_cols[:5]:
                    unique = self.df[col].nunique()
                    top = self.df[col].mode().iloc[0] if len(self.df[col].mode()) > 0 else "N/A"
                    lines.append(f"  • {col}: {unique} unique, top='{top}'")
                if len(cat_cols) > 5:
                    lines.append(f"  ... and {len(cat_cols) - 5} more")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error describing data: {str(e)}"
    
    def show_missing(self) -> str:
        """Show missing value analysis."""
        if not self.is_loaded:
            return "No dataset loaded."
        
        missing = self.df.isnull().sum()
        missing = missing[missing > 0].sort_values(ascending=False)
        
        if len(missing) == 0:
            return "✅ No missing values in the dataset!"
        
        lines = ["🔍 Missing Values Analysis", ""]
        
        total_cells = self.df.shape[0] * self.df.shape[1]
        total_missing = self.df.isnull().sum().sum()
        overall_pct = (total_missing / total_cells) * 100
        
        lines.append(f"Overall: {total_missing:,} missing ({overall_pct:.2f}%)")
        lines.append("")
        lines.append("By column:")
        
        for col, count in missing.items():
            pct = (count / len(self.df)) * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            lines.append(f"  {col}: {count:,} ({pct:.1f}%) {bar}")
        
        return "\n".join(lines)
    
    def show_columns(self) -> str:
        """Show column information."""
        if not self.is_loaded:
            return "No dataset loaded."
        
        lines = ["📋 Column Information", ""]
        
        for col in self.df.columns:
            dtype = self.df[col].dtype
            non_null = self.df[col].count()
            unique = self.df[col].nunique()
            
            lines.append(f"**{col}**")
            lines.append(f"  Type: {dtype}")
            lines.append(f"  Non-null: {non_null:,} / {len(self.df):,}")
            lines.append(f"  Unique: {unique:,}")
            
            # Sample values
            sample = self.df[col].dropna().head(3).tolist()
            if sample:
                sample_str = ", ".join(str(v)[:20] for v in sample)
                lines.append(f"  Sample: {sample_str}")
            lines.append("")
        
        return "\n".join(lines)
    
    def show_sample(self, n: int = 5) -> str:
        """Show sample rows."""
        if not self.is_loaded:
            return "No dataset loaded."
        
        try:
            sample = self.df.head(n).to_string()
            return f"📋 First {n} rows:\n\n{sample}"
        except Exception as e:
            return f"Error showing sample: {str(e)}"
    
    def show_shape(self) -> str:
        """Show dataset shape."""
        if not self.is_loaded:
            return "No dataset loaded."
        
        return f"📏 Shape: {self.df.shape[0]:,} rows × {self.df.shape[1]} columns"
    
    def show_dtypes(self) -> str:
        """Show column data types."""
        if not self.is_loaded:
            return "No dataset loaded."
        
        lines = ["📊 Data Types", ""]
        
        dtype_counts = self.df.dtypes.value_counts()
        for dtype, count in dtype_counts.items():
            lines.append(f"  {dtype}: {count} columns")
        
        lines.append("")
        lines.append("By column:")
        for col, dtype in self.df.dtypes.items():
            lines.append(f"  • {col}: {dtype}")
        
        return "\n".join(lines)
    
    def get_correlation(self, method: str = "pearson") -> str:
        """Get correlation matrix for numeric columns."""
        if not self.is_loaded:
            return "No dataset loaded."
        
        numeric_df = self.df.select_dtypes(include=['number'])
        
        if numeric_df.empty:
            return "No numeric columns for correlation analysis."
        
        try:
            corr = numeric_df.corr(method=method)
            
            lines = [f"📊 Correlation Matrix ({method})", ""]
            
            # Find high correlations
            high_corr = []
            for i in range(len(corr.columns)):
                for j in range(i + 1, len(corr.columns)):
                    val = corr.iloc[i, j]
                    if abs(val) > 0.5:
                        high_corr.append((corr.columns[i], corr.columns[j], val))
            
            if high_corr:
                lines.append("High correlations (|r| > 0.5):")
                for col1, col2, val in sorted(high_corr, key=lambda x: -abs(x[2])):
                    lines.append(f"  • {col1} ↔ {col2}: {val:.3f}")
            else:
                lines.append("No high correlations found (|r| > 0.5)")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error computing correlation: {str(e)}"
    
    def value_counts(self, column: str, top_n: int = 10) -> str:
        """Get value counts for a column."""
        if not self.is_loaded:
            return "No dataset loaded."
        
        if column not in self.df.columns:
            return f"Column '{column}' not found."
        
        try:
            counts = self.df[column].value_counts().head(top_n)
            
            lines = [f"📊 Value Counts for '{column}'", ""]
            
            for value, count in counts.items():
                pct = (count / len(self.df)) * 100
                lines.append(f"  {value}: {count:,} ({pct:.1f}%)")
            
            if self.df[column].nunique() > top_n:
                lines.append(f"  ... and {self.df[column].nunique() - top_n} more values")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error getting value counts: {str(e)}"
