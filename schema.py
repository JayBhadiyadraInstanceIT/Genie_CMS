from pydantic import BaseModel
from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional, List

# class HostOutput(BaseModel):
#     text: str
#     project_inquiry: bool


class StatePayload(BaseModel):
    state: Dict[str, Any]


class CustomStreamRequest(BaseModel):
    text: str


class CreateSessionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    session_id: Optional[str] = None
    state: Optional[Dict[str, Any]] = None


class ChatPayload(BaseModel):
    text: str


class Part(BaseModel):
    text: str


class ChatMessage(BaseModel):
    role: str
    parts: List[Part]


class ChatRequest(BaseModel):
    app_name: str
    user_id: str
    session_id: str
    new_message: ChatMessage


class SessionResponse(BaseModel):
    user_id: str
    session_id: str
    app_name: str
    status: str
    state: Optional[Dict[str, Any]]