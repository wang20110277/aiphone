import pytest
from graph_flow import create_call_graph, CallGraphState


def test_graph_creation():
    graph = create_call_graph()
    assert graph is not None


@pytest.mark.asyncio
async def test_graph_runs_recall_to_execute():
    graph = create_call_graph()
    state: CallGraphState = {
        "fs_uuid": "test-uuid",
        "biz_type": "marketing",
        "user_key": "user1:hash1",
        "user_input": "你好",
        "memory_block": "",
        "rag_block": "",
        "llm_action": None,
        "identity_verified": False,
        "turn_count": 1,
        "handoff_reason": "",
    }
    result = await graph.ainvoke(state)
    assert result["llm_action"] is not None
    assert result["llm_action"].type in ("say", "ask", "handoff", "end")
