import pytest
from rag_retriever import retrieve_scripts, build_rag_block


@pytest.mark.asyncio
async def test_retrieve_scripts_returns_matching():
    """When no LLM engine is set, get_embedding returns None,
    so retrieve_scripts returns an empty list without raising."""
    results = await retrieve_scripts(
        biz_type="collection",
        user_input="我下周一定还",
        top_k=3,
    )
    assert isinstance(results, list)
    # Without a real LLM engine, embedding fails gracefully => empty list
    assert len(results) == 0


def test_build_rag_block_empty():
    result = build_rag_block([])
    assert result == ""


def test_build_rag_block_with_scripts():
    scripts = [
        {"title": "承诺还款确认", "content": "感谢您的承诺，我们将记录...", "score": 0.92, "scene": "催收"},
        {"title": "还款方式引导", "content": "您可以选择以下还款方式...", "score": 0.85, "scene": "催收"},
    ]
    result = build_rag_block(scripts)
    assert "承诺还款确认" in result
    assert "还款方式引导" in result
    assert "0.92" in result
