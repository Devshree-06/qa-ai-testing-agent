
from typing import TypedDict

from langgraph.graph import MessagesState

class AgentState(MessagesState):
    project_path:str
    framework: str