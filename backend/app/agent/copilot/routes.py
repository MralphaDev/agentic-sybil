"""FastAPI routes for Investigation Copilot."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.agent.copilot.models import CopilotRequest
from app.agent.copilot.service import _stream_answer

router = APIRouter(prefix="/investigations", tags=["Investigation Copilot"])

@router.post("/copilot/stream")
async def copilot_stream(request: CopilotRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_answer(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
