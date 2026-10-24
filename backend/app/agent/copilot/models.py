"""Request models for the Investigation Copilot API."""
from pydantic import BaseModel, Field
from app.agent.copilot.common import MAX_QUESTION_CHARS

class CopilotRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
