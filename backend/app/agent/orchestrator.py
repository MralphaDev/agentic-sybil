
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable
import json

from pydantic import BaseModel

from app.agent.context import AnalysisContext
from app.agent.graph import build_agent_graph
from app.agent.state import AgentState
from app.agent.sse_manager import get_current_event_callback


EventCallback = Callable[[str, Any], None]


def _to_json_safe(value: Any) -> Any:
    """
    Convert values into JSON-safe structures for SSE payloads.

    Handles Pydantic models, datetime objects, enums, nested containers,
    and unexpected objects without requiring a specific schema.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Enum):
        return _to_json_safe(value.value)

    if isinstance(value, BaseModel):
        return _to_json_safe(value.model_dump(mode="json"))

    if isinstance(value, dict):
        return {
            str(key): _to_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _to_json_safe(model_dump(mode="json"))
        except Exception:
            pass

    return str(value)


def _message_content(message: Any) -> Any:
    """Extract message content without assuming it is a plain string."""
    return _to_json_safe(getattr(message, "content", None))


def run_agent_investigation(
    context: AnalysisContext,
    emit_event: EventCallback | None = None,
) -> dict[str, Any]:
    """
    Run the agent investigation and optionally forward activity through SSE.

    An explicitly supplied emit_event callback takes priority.
    Otherwise, use the callback registered in sse_manager's ContextVar.
    """

    # Connect to the callback registered by run_pipeline().
    if emit_event is None:
        emit_event = get_current_event_callback()

    def emit(event_type: str, data: Any = None) -> None:
        if emit_event is None:
            return

        safe_data = _to_json_safe(data)

        try:
            # Validate serializability before passing data to the transport.
            json.dumps(safe_data, ensure_ascii=False)
            emit_event(event_type, safe_data)
        except Exception as exc:
            # Streaming is supplementary; it must not break the analysis.
            print(f"[SSE] Failed to emit {event_type}: {exc}")

    graph = build_agent_graph(context)

    initial_state: AgentState = {
        "messages": [],
        "initial_observation": {},
        "investigation_round": 0,
        "investigation_complete": False,
    }

    result: dict[str, Any] = {}

    print("\n========== Agent Investigation Started ==========")
    emit("status", {"message": "Agent investigation started"})

    try:
        for mode, payload in graph.stream(
            initial_state,
            stream_mode=["values", "custom"],
        ):
            # ---------------------------------------------------------
            # Custom events emitted by LangGraph nodes or tools.
            # ---------------------------------------------------------
            if mode == "custom":
                if isinstance(payload, dict):
                    event_type = payload.get("type", "agent_event")
                    emit(event_type, payload)
                else:
                    emit("agent_event", {"content": payload})

                continue

            if mode != "values":
                continue

            if not isinstance(payload, dict):
                print(
                    "[Agent Warning] Ignoring unexpected graph state: "
                    f"{type(payload).__name__}"
                )
                continue

            result = payload

            # ---------------------------------------------------------
            # Initial observation and investigation progress.
            # ---------------------------------------------------------
            observation = payload.get("initial_observation")
            if observation:
                emit("initial_observation", observation)

            emit(
                "progress",
                {
                    "investigation_round": payload.get(
                        "investigation_round", 0
                    ),
                    "investigation_complete": payload.get(
                        "investigation_complete", False
                    ),
                },
            )

            # ---------------------------------------------------------
            # Latest LangChain message.
            # ---------------------------------------------------------
            messages = payload.get("messages", [])

            if not isinstance(messages, (list, tuple)) or not messages:
                continue

            message = messages[-1]

            # Tool calls are generally dictionaries.
            tool_calls = getattr(message, "tool_calls", []) or []

            if isinstance(tool_calls, (list, tuple)):
                for call in tool_calls:
                    if not isinstance(call, dict):
                        continue

                    tool_name = call.get("name", "unknown")
                    tool_args = call.get("args", {})

                    print(f"\n[Tool Call] {tool_name}")
                    print(f"[Tool Input] {_to_json_safe(tool_args)}")

                    emit(
                        "tool_call",
                        {
                            "name": tool_name,
                            "args": tool_args,
                        },
                    )

            # ---------------------------------------------------------
            # Agent messages.
            # ---------------------------------------------------------
            message_type = getattr(message, "type", None)

            if message_type == "ai":
                content = _message_content(message)

                if content not in (None, ""):
                    emit(
                        "agent_message",
                        {
                            "content": content,
                            "investigation_round": payload.get(
                                "investigation_round", 0
                            ),
                        },
                    )

    except Exception as exc:
        print(f"\n[Agent Error] {exc}")
        emit("error", {"message": str(exc)})
        raise

    print("\n========== Agent Investigation Finished ==========")

    # -------------------------------------------------------------
    # Extract the final AI response.
    # -------------------------------------------------------------
    messages = result.get("messages", [])
    final_response = None

    if isinstance(messages, (list, tuple)) and messages:
        last_message = messages[-1]

        if (
            getattr(last_message, "type", None) == "ai"
            and not getattr(last_message, "tool_calls", [])
        ):
            final_response = _message_content(last_message)

    final_result = {
        "initial_observation": _to_json_safe(
            result.get("initial_observation", {})
        ),
        "investigation_round": result.get("investigation_round", 0),
        "investigation_complete": result.get(
            "investigation_complete", False
        ),
        "final_response": final_response,
    }

    emit("final_response", {"content": final_response})
    emit("status", {"message": "Agent investigation finished"})

    return final_result
