import logging
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from llm_base import LLMAction, parse_llm_response, FALLBACK_ACTION_TEXT

logger = logging.getLogger(__name__)


class CallGraphState(TypedDict):
    fs_uuid: str
    biz_type: str
    user_key: str
    user_input: str
    memory_block: str
    rag_block: str
    llm_action: Optional[LLMAction]
    identity_verified: bool
    turn_count: int
    handoff_reason: str


# --- 节点函数 ---

async def recall_memory_node(state: CallGraphState) -> dict:
    # Phase 6 实现实际记忆召回
    return {"memory_block": ""}


async def rag_retrieve_node(state: CallGraphState) -> dict:
    """Agentic RAG: 根据用户输入检索最相关话术"""
    from rag_retriever import retrieve_scripts, build_rag_block
    scripts = await retrieve_scripts(
        biz_type=state["biz_type"],
        user_input=state["user_input"],
    )
    return {"rag_block": build_rag_block(scripts)}


async def llm_decide_node(state: CallGraphState) -> dict:
    # Phase 5 先用规则引擎
    from event_handlers import RULES, DEFAULT_REPLY
    reply = RULES.get(state["biz_type"], DEFAULT_REPLY)
    action = LLMAction(type="say", text=reply, intent="default")
    return {"llm_action": action}


async def compliance_check_node(state: CallGraphState) -> dict:
    action = state["llm_action"]
    if action and state["biz_type"] == "collection" and not state["identity_verified"]:
        action.text = _sanitize_sensitive(action.text)
    return {"llm_action": action}


async def execute_action_node(state: CallGraphState) -> dict:
    action = state["llm_action"]
    if action and action.type == "handoff":
        return {"handoff_reason": action.intent, "turn_count": state["turn_count"]}
    return {"turn_count": state["turn_count"]}


async def finalize_node(state: CallGraphState) -> dict:
    logger.info(f"[{state['fs_uuid']}] finalize")
    return {}


def _sanitize_sensitive(text: str) -> str:
    import re
    return re.sub(r'\d{4,}', '****', text)


# --- 条件边 ---

def route_after_llm(state: CallGraphState) -> str:
    if state["biz_type"] == "collection" and not state["identity_verified"]:
        return "compliance_check"
    return "execute_action"


def route_after_execute(state: CallGraphState) -> str:
    action = state["llm_action"]
    if action and action.type in ("end", "handoff"):
        return "finalize"
    return END


# --- 构建图 ---

def create_call_graph():
    graph = StateGraph(CallGraphState)

    graph.add_node("recall_memory", recall_memory_node)
    graph.add_node("rag_retrieve", rag_retrieve_node)
    graph.add_node("llm_decide", llm_decide_node)
    graph.add_node("compliance_check", compliance_check_node)
    graph.add_node("execute_action", execute_action_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("recall_memory")
    graph.add_edge("recall_memory", "rag_retrieve")
    graph.add_edge("rag_retrieve", "llm_decide")
    graph.add_conditional_edges("llm_decide", route_after_llm, {
        "compliance_check": "compliance_check",
        "execute_action": "execute_action",
    })
    graph.add_edge("compliance_check", "execute_action")
    graph.add_conditional_edges("execute_action", route_after_execute, {
        "finalize": "finalize",
        END: END,
    })

    return graph.compile()
