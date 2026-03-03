import os
import sys

# Ensure src in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from langchain_core.messages import HumanMessage

from heart_speaks.graph import app


def test_graph_compiles_and_responds():
    """Simple smoke test to ensure graph compiles and doesn't crash on standard input."""
    # This requires an OPENAI_API_KEY to be set in .env
    inputs = {"messages": [HumanMessage(content="What is true peace?")]}
    
    try:
        result = app.invoke(inputs)
        assert "final_response" in result
        assert "answer" in result["final_response"]
        assert isinstance(result["final_response"]["answer"], str)
    except Exception as e:
        pytest.fail(f"Graph invocation failed with {e}")
