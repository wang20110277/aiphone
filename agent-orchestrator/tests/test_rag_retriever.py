import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from rag.retriever import (
    retrieve_scripts, build_rag_block,
    should_retrieve, grade_documents, rewrite_query,
    GradeRetrieval, GradeDocuments, RewrittenQuery,
)


def test_build_rag_block_empty():
    assert build_rag_block([]) == ""


def test_build_rag_block_with_scripts():
    scripts = [
        {"title": "问候", "content": "您好", "scene": "greeting", "score": 0.9},
    ]
    result = build_rag_block(scripts)
    assert "问候" in result
    assert "参考话术" in result


def _make_llm_mock(ainvoke_return=None, ainvoke_side_effect=None):
    """Build a mock LLM service matching: llm._chat.with_structured_output(...).ainvoke(...)

    Source code pattern:
        structured = llm._chat.with_structured_output(Schema, method="json_mode")
        result = await structured.ainvoke(messages)
    """
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(
        return_value=ainvoke_return,
        side_effect=ainvoke_side_effect,
    )
    mock_llm._chat.with_structured_output.return_value = mock_chain
    return mock_llm


@pytest.mark.asyncio
async def test_should_retrieve_yes():
    mock_llm = _make_llm_mock(ainvoke_return=GradeRetrieval(binary_score="yes"))
    with patch("rag.retriever.get_llm_service", return_value=mock_llm):
        result = await should_retrieve("你们的产品有什么优惠", "marketing")
    assert result is True


@pytest.mark.asyncio
async def test_should_retrieve_no():
    mock_llm = _make_llm_mock(ainvoke_return=GradeRetrieval(binary_score="no"))
    with patch("rag.retriever.get_llm_service", return_value=mock_llm):
        result = await should_retrieve("好的谢谢", "customer_service")
    assert result is False


@pytest.mark.asyncio
async def test_should_retrieve_failure_defaults_to_true():
    mock_llm = _make_llm_mock(ainvoke_side_effect=Exception("LLM error"))
    with patch("rag.retriever.get_llm_service", return_value=mock_llm):
        result = await should_retrieve("test", "marketing")
    assert result is True


@pytest.mark.asyncio
async def test_grade_documents_filters_irrelevant():
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    # First doc: relevant, second: irrelevant
    mock_chain.ainvoke = AsyncMock(side_effect=[
        GradeDocuments(binary_score="relevant"),
        GradeDocuments(binary_score="irrelevant"),
    ])
    mock_llm._chat.with_structured_output.return_value = mock_chain
    scripts = [
        {"content": "相关内容"},
        {"content": "不相关内容"},
    ]
    with patch("rag.retriever.get_llm_service", return_value=mock_llm):
        result = await grade_documents("用户问题", scripts)
    assert len(result) == 1
    assert result[0]["content"] == "相关内容"


@pytest.mark.asyncio
async def test_grade_documents_empty():
    result = await grade_documents("test", [])
    assert result == []


@pytest.mark.asyncio
async def test_rewrite_query():
    mock_llm = _make_llm_mock(ainvoke_return=RewrittenQuery(query="产品价格优惠活动"))
    with patch("rag.retriever.get_llm_service", return_value=mock_llm):
        result = await rewrite_query("有什么优惠", [{"title": "t", "content": "c"}])
    assert result == "产品价格优惠活动"


@pytest.mark.asyncio
async def test_rewrite_query_failure_returns_original():
    mock_llm = _make_llm_mock(ainvoke_side_effect=Exception("error"))
    with patch("rag.retriever.get_llm_service", return_value=mock_llm):
        result = await rewrite_query("原始查询", [])
    assert result == "原始查询"
