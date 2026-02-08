"""
AgentZero AgentState schema for LangGraph orchestration.
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    user_input: str
    intent: Optional[str] = None
    plan: Optional[List[Dict[str, Any]]] = None
    context: Optional[Dict[str, Any]] = None
    memory: Dict[str, Any] = Field(default_factory=dict)  # STM, LTM, structured
    tool_results: Optional[List[Dict[str, Any]]] = None
    audit_log: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    permissions: Dict[str, bool] = Field(default_factory=dict)
    response: Optional[str] = None
    step: Optional[str] = None  # Current node/state

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"
