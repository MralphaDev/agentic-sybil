
import asyncio
import io
import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.agent.sse_manager import (
    create_run,
    get_run,
    encode_sse,
    set_current_event_callback,
    reset_current_event_callback,
)
from app.services.ingestion_service import ingest_forensic_csv
from app.services.analysis_service import execute_analysis


router = APIRouter(
    prefix="/investigations",
    tags=["Investigations"],
)


async def run_pipeline(
    run_id: str,
    file_bytes: bytes,
    filename: str,
    token_address: str,
) -> None:
    """Run ingestion and analysis after the upload response has returned."""

    run = get_run(run_id)
    if run is None:
        return

    loop = asyncio.get_running_loop()

    # The agent callback is synchronous, but run.emit() is asynchronous.
    # This bridge also works when callbacks originate in a worker thread.
    def emit_event(event_type: str, data: Any = None) -> None:
        event = {
            "type": event_type,
            "timestamp": None,
            "data": data,
        }

        def enqueue_event() -> None:
            asyncio.create_task(run.queue.put(event))

        loop.call_soon_threadsafe(enqueue_event)

    callback_token = set_current_event_callback(emit_event)

    try:
        run.status = "processing"
        await run.emit("status", {"message": "Ingestion started"})

        uploaded_file = StarletteUploadFile(
            file=io.BytesIO(file_bytes),
            filename=filename,
            size=len(file_bytes),
        )

        ingestion_result = await ingest_forensic_csv(
            file=uploaded_file,
            token_address=token_address,
        )

        await run.emit(
            "status",
            {"message": "Ingestion finished; analysis started"},
        )

        # execute_analysis() is synchronous, so keep it off the event loop.
        analysis_result = await asyncio.to_thread(
            execute_analysis,
            target_token_mint=token_address,
        )

        run.result = {
            "ingestion": ingestion_result,
            "analysis": analysis_result,
        }
        run.status = "completed"

        await run.emit(
            "completed",
            {
                "run_id": run_id,
                "message": "Investigation pipeline completed",
            },
        )

    except Exception as exc:
        run.error = str(exc)
        run.status = "error"

        await run.emit(
            "error",
            {"message": str(exc)},
        )

    finally:
        reset_current_event_callback(callback_token)


@router.post("/upload", status_code=202)
async def upload_investigation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    token_address: str = Form(...),
) -> dict:
    """Accept an upload, create a run, and schedule background processing."""

    token_address = token_address.strip()

    if not token_address:
        raise HTTPException(
            status_code=400,
            detail="token_address must not be empty",
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A CSV filename is required",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty",
        )

    run = create_run()

    background_tasks.add_task(
        run_pipeline,
        run.run_id,
        file_bytes,
        file.filename,
        token_address,
    )

    return {
        "run_id": run.run_id,
        "status": run.status,
    }


@router.get("/stream/{run_id}")
async def stream_investigation(run_id: str):
    run = get_run(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found",
        )

    async def event_generator():
        yield encode_sse({
            "type": "connected",
            "data": {"run_id": run_id},
        })

        while True:
            try:
                event = await asyncio.wait_for(
                    run.queue.get(),
                    timeout=15,
                )
                yield encode_sse(event)

                if event["type"] in {"completed", "error"}:
                    break

            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/result/{run_id}")
async def get_investigation_result(run_id: str) -> dict:
    run = get_run(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found",
        )

    if run.error:
        return {
            "run_id": run_id,
            "status": "error",
            "error": run.error,
        }

    return {
        "run_id": run_id,
        "status": run.status,
        "result": run.result,
    }
