import sys
import os
from google.adk.agents import LlmAgent
from prompt import instruction
from cms_tools import get_mongodb_tool

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from constants import (
    MODEL, 
    REMOTE_1_AGENT_NAME,
    )

def create_agent() -> LlmAgent:
    """Constructs the ADK agent for RemoteAgent."""
    return LlmAgent(
        model=MODEL,
        name=REMOTE_1_AGENT_NAME,
        description="Specialized agent for querying MongoDB collections via Node.js API",
        instruction = instruction,
        tools=[get_mongodb_tool],
    )
