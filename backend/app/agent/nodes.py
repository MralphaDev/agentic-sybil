from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from app.agent.context import AnalysisContext
from app.agent.llm import llm
from app.agent.prompts.investigation import INVESTIGATION_SYSTEM_PROMPT
from app.agent.state import AgentState, MAX_INVESTIGATION_ROUNDS
from app.agent.tools.wallet_age import analyze_four_hour_wallet_age


def initial_observation_node(
    context: AnalysisContext,
) -> dict[str, Any]:
    writer = get_stream_writer()

    writer({
        "type": "status",
        "message": "Analyzing initial wallet activity...",
    })

    result = analyze_four_hour_wallet_age(context)

    print("\n[Initial Observation]")
    print(result)

    writer({
        "type": "initial_observation",
        "content": str(result),
    })

    return {
        "initial_observation": result,
        "investigation_round": 0,
        "investigation_complete": False,
    }


def decision_node(
    state: AgentState,
    context: AnalysisContext,
    tools: list[Any],
) -> dict[str, Any]:
    writer = get_stream_writer()

    current_round = state["investigation_round"]
    force_final = current_round >= MAX_INVESTIGATION_ROUNDS

    if force_final:
        messages = [
            SystemMessage(content=INVESTIGATION_SYSTEM_PROMPT),
            *state["messages"],
            HumanMessage(
                content=(
                    "MANDATORY FINALIZATION.\n"
                    f"Initial observation:\n"
                    f"{state['initial_observation']}\n\n"
                    f"Investigation round: {current_round} / "
                    f"{MAX_INVESTIGATION_ROUNDS}\n\n"
                    "The investigation limit has been reached. Produce "
                    "the final report NOW, based only on the evidence "
                    "collected so far and the initial observation.\n"
                    "Do not call tools. Do not output tool-call markup. "
                    "Do not postpone the verdict. If evidence is "
                    "incomplete, state the uncertainty and give the "
                    "best-supported conclusion in the required format."
                )
            ),
        ]
        model = llm
    else:
        messages = [
            SystemMessage(content=INVESTIGATION_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Initial observation:\n"
                    f"{state['initial_observation']}\n\n"
                    f"Investigation round: {current_round} / "
                    f"{MAX_INVESTIGATION_ROUNDS}\n\n"
                    "Investigate selectively using available tools. "
                    "Avoid repeating analyses unnecessarily. Maintain "
                    "your current hypothesis and supporting evidence. "
                    "Distinguish observed facts from interpretations. "
                    "When sufficient evidence is available, provide "
                    "the final report in the required format."
                )
            ),
            *state["messages"],
        ]
        model = llm.bind_tools(tools)

    print(f"\n[LLM Decision] Investigation round: {current_round}")

    writer({
        "type": "status",
        "round": current_round,
        "message": (
            "Preparing final report..."
            if force_final
            else f"Investigating (round {current_round})..."
        ),
    })

    # Stream chunks while accumulating the complete AI message.
    response = None
    streamed_text = False

    for chunk in model.stream(messages):
        if response is None:
            response = chunk
        else:
            response += chunk

        # Stream only visible text, not internal reasoning.
        if chunk.content:
            if isinstance(chunk.content, str):
                content = chunk.content
            elif isinstance(chunk.content, list):
                # Some providers return content blocks.
                content = "".join(
                    block.get("text", "")
                    for block in chunk.content
                    if isinstance(block, dict)
                    and block.get("type") == "text"
                )
            else:
                content = ""

            if content:
                streamed_text = True
                print(content, end="", flush=True)

                writer({
                    "type": "llm_token",
                    "round": current_round,
                    "content": content,
                })

    print()

    if response is None:
        raise RuntimeError("LLM returned no response.")

    usage = getattr(response, "usage_metadata", None)
    if usage:
        print(f"[Token Usage] {usage}")
        writer({
            "type": "token_usage",
            "usage": usage,
        })

    tool_calls = getattr(response, "tool_calls", [])

    if force_final and tool_calls:
        raise RuntimeError(
            "Finalization returned tool calls instead of a final report."
        )

    if tool_calls:
        for call in tool_calls:
            name = call.get("name")
            args = call.get("args", {})

            print(f"\n[Tool Call] {name}")
            print(f"[Tool Input] {args}")

            writer({
                "type": "tool_call",
                "round": current_round,
                "name": name,
                "args": args,
            })

    else:
        print("\n[Final Agent Response]")
        print(response.content) #type:ignore

        writer({
            "type": "final_response",
            "content": response.content,#type:ignore
        })

    return {
        "messages": [response],
        "investigation_complete": force_final or not bool(tool_calls),
    }