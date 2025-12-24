"""
Tests for enhanced agent tools.
"""

import pytest
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestWebSearchTool:
    """Tests for web search tool."""
    
    def test_search_execution(self):
        """Test web search executes without error."""
        from src.agents.tools_enhanced import WebSearchTool
        
        tool = WebSearchTool(max_results=2)
        result = tool.execute(query="Python programming")
        
        # May fail if duckduckgo-search not installed
        if result.success:
            assert "results" in result.data
            assert len(result.data["results"]) <= 2


class TestCalculatorTool:
    """Tests for calculator tool."""
    
    def test_basic_math(self):
        """Test basic calculations."""
        from src.agents.tools_enhanced import CalculatorTool
        
        tool = CalculatorTool()
        
        result = tool.execute(expression="2 + 2")
        assert result.success
        assert result.data["result"] == 4
        
        result = tool.execute(expression="10 * 5")
        assert result.success
        assert result.data["result"] == 50
    
    def test_math_functions(self):
        """Test math functions."""
        from src.agents.tools_enhanced import CalculatorTool
        
        tool = CalculatorTool()
        
        result = tool.execute(expression="sqrt(16)")
        assert result.success
        assert result.data["result"] == 4.0
        
        result = tool.execute(expression="sin(0)")
        assert result.success
        assert result.data["result"] == 0.0
    
    def test_invalid_expression(self):
        """Test invalid expressions."""
        from src.agents.tools_enhanced import CalculatorTool
        
        tool = CalculatorTool()
        
        result = tool.execute(expression="invalid")
        assert not result.success
        assert result.error is not None


class TestFileTools:
    """Tests for file tools."""
    
    def test_file_write_read(self):
        """Test file write and read."""
        from src.agents.tools_enhanced import FileWriteTool, FileReadTool
        
        write_tool = FileWriteTool()
        read_tool = FileReadTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            content = "Hello, JARVIS!"
            
            # Write
            result = write_tool.execute(path=str(test_file), content=content)
            assert result.success
            
            # Read
            result = read_tool.execute(path=str(test_file))
            assert result.success
            assert result.output == content
    
    def test_file_not_found(self):
        """Test reading non-existent file."""
        from src.agents.tools_enhanced import FileReadTool
        
        tool = FileReadTool()
        result = tool.execute(path="/nonexistent/file.txt")
        
        assert not result.success
        assert "not found" in result.error.lower()


class TestCodeExecutionTool:
    """Tests for code execution tool."""
    
    def test_simple_code(self):
        """Test simple code execution."""
        from src.agents.tools_enhanced import CodeExecutionTool
        
        tool = CodeExecutionTool(timeout=10)
        
        result = tool.execute(code="print('Hello, World!')")
        assert result.success
        assert "Hello, World!" in result.output
    
    def test_calculation(self):
        """Test calculation in code."""
        from src.agents.tools_enhanced import CodeExecutionTool
        
        tool = CodeExecutionTool(timeout=10)
        
        result = tool.execute(code="print(sum(range(10)))")
        assert result.success
        assert "45" in result.output
    
    def test_syntax_error(self):
        """Test handling syntax errors."""
        from src.agents.tools_enhanced import CodeExecutionTool
        
        tool = CodeExecutionTool(timeout=10)
        
        result = tool.execute(code="print('unclosed")
        assert not result.success


class TestToolRegistry:
    """Tests for tool registry."""
    
    def test_registry_creation(self):
        """Test creating default registry."""
        from src.agents.tools_enhanced import create_default_registry
        
        registry = create_default_registry()
        tools = registry.list_tools()
        
        assert len(tools) > 0
        
        # Check essential tools exist
        tool_names = [t["name"] for t in tools]
        assert "web_search" in tool_names
        assert "calculator" in tool_names
        assert "file_read" in tool_names
    
    def test_registry_execute(self):
        """Test executing tool through registry."""
        from src.agents.tools_enhanced import create_default_registry
        
        registry = create_default_registry()
        
        result = registry.execute("calculator", expression="1 + 1")
        assert result.success
        assert result.data["result"] == 2
    
    def test_registry_unknown_tool(self):
        """Test executing unknown tool."""
        from src.agents.tools_enhanced import create_default_registry
        
        registry = create_default_registry()
        
        result = registry.execute("unknown_tool")
        assert not result.success
        assert "not found" in result.error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
