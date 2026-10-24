
from typing import Any
from typing_extensions import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]
    initial_observation: dict[str, Any]
    investigation_round: int
    investigation_complete: bool
    #clustering_required: bool
    #clustering_done: bool


MAX_INVESTIGATION_ROUNDS = 4
