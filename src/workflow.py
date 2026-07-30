"""LangGraph definition for classifying, responding to, and resetting chats."""

from langgraph.graph import END, StateGraph

from src.intent import determine_intent
from src.model_inference import ModelInference
from src.state import BotState


def next_step(state: BotState) -> str:
    if not state.get("is_addressed"):
        return "ignore"
    if state["prompt"].strip().lower() == "!reset":
        return "reset"
    return "respond"


def build_workflow(model: ModelInference):
    """Build the executable graph with this application's model instance."""

    async def classify(state: BotState) -> BotState:
        return await determine_intent(model, state)

    async def respond(state: BotState) -> BotState:
        return {"answer": await model.answer(state["channel_id"], state["prompt"])}

    def reset(state: BotState) -> BotState:
        model.clear_history(state["channel_id"])
        return {"reset": True}

    workflow = StateGraph(BotState)
    workflow.add_node("determine_intent", classify)
    workflow.add_node("respond", respond)
    workflow.add_node("reset", reset)
    workflow.set_entry_point("determine_intent")
    workflow.add_conditional_edges(
        "determine_intent",
        next_step,
        {"ignore": END, "reset": "reset", "respond": "respond"},
    )
    workflow.add_edge("respond", END)
    workflow.add_edge("reset", END)
    return workflow.compile()
