import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from adapter.base import ASREngine, ASRResult
from adapter.engines.sensevoice.engine import SenseVoiceASREngine


@pytest.fixture
def engine():
    with patch.dict("os.environ", {
        "SENSEVOICE_API_URL": "http://funasr:8000",
        "SENSEVOICE_TIMEOUT": "30",
        "SENSEVOICE_LANGUAGE": "zh",
        "SENSEVOICE_MAX_CONCURRENCY": "10",
    }):
        return SenseVoiceASREngine()


def _mock_async_client(response_json=None, response_status=200, side_effect=None):
    """Build a mock httpx.AsyncClient that can be used as an async context manager."""
    mock_response = MagicMock()
    mock_response.status_code = response_status
    mock_response.json.return_value = response_json or {}

    mock_client = AsyncMock()
    if side_effect:
        mock_client.post = AsyncMock(side_effect=side_effect)
        mock_client.get = AsyncMock(side_effect=side_effect)
    else:
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.get = AsyncMock(return_value=mock_response)

    # Support `async with httpx.AsyncClient() as client:`
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return mock_client


# ── Tests ──────────────────────────────────────────────────────────────


def test_engine_inherits_base():
    eng = SenseVoiceASREngine()
    assert isinstance(eng, ASREngine)


@pytest.mark.asyncio
async def test_health_check_success(engine):
    mock_client = _mock_async_client(response_status=200)

    with patch(
        "adapter.engines.sensevoice.engine.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await engine.health_check()

    assert result is True
    mock_client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_check_failure(engine):
    mock_client = _mock_async_client(side_effect=Exception("connection refused"))

    with patch(
        "adapter.engines.sensevoice.engine.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await engine.health_check()

    assert result is False


@pytest.mark.asyncio
async def test_recognize_success(engine):
    mock_client = _mock_async_client(
        response_json={"text": "你好世界", "confidence": 0.95},
        response_status=200,
    )

    with patch(
        "adapter.engines.sensevoice.engine.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await engine.recognize(b"fake-audio-bytes", {})

    assert isinstance(result, ASRResult)
    assert result.text == "你好世界"
    assert result.confidence == 0.95
    assert result.is_final is True
    mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_recognize_server_error(engine):
    mock_client = _mock_async_client(
        side_effect=Exception("internal server error"),
    )

    with patch(
        "adapter.engines.sensevoice.engine.httpx.AsyncClient",
        return_value=mock_client,
    ):
        with pytest.raises(RuntimeError, match="SenseVoice recognition failed"):
            await engine.recognize(b"fake-audio-bytes", {})


@pytest.mark.asyncio
async def test_recognize_semaphore_limits_concurrency(engine):
    mock_client = _mock_async_client(
        response_json={"text": "测试", "confidence": 0.9},
        response_status=200,
    )

    # Spy on the semaphore's __aenter__ to verify it is used
    original_aenter = engine._semaphore.__aenter__
    aenter_called = False

    async def spy_aenter(*args, **kwargs):
        nonlocal aenter_called
        aenter_called = True
        return await original_aenter(*args, **kwargs)

    engine._semaphore.__aenter__ = spy_aenter

    with patch(
        "adapter.engines.sensevoice.engine.httpx.AsyncClient",
        return_value=mock_client,
    ):
        await engine.recognize(b"fake-audio-bytes", {})

    assert aenter_called, "Semaphore __aenter__ was not called during recognize"
