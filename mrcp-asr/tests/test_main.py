import pytest
from httpx import AsyncClient, ASGITransport
from adapter.main import app, _load_config, engine as _engine_ref
from adapter.config import load_asr_engine


@pytest.mark.asyncio
async def test_healthz():
    import adapter.main as main_mod
    config = _load_config()
    main_mod.engine = load_asr_engine(config["engine"]["asr"])
    if hasattr(main_mod.engine, "load_model"):
        await main_mod.engine.load_model()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
