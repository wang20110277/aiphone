import os
import json
import yaml
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form
from fastapi.responses import Response
from adapter.config import load_tts_engine
from adapter import storage

logger = logging.getLogger(__name__)
engine = None


def _load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    config = _load_config()
    engine = load_tts_engine(config["engine"]["tts"])
    if hasattr(engine, "load_model"):
        await engine.load_model()
    logger.info(f"TTS engine loaded: {config['engine']['tts']}")
    yield


app = FastAPI(title="TTS Adapter Service", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    healthy = await engine.health_check() if engine else False
    return {"status": "ok" if healthy else "degraded"}


@app.post("/tts/synthesize")
async def synthesize(text: str = Form(...), params: str = Form("{}")):
    params_dict = json.loads(params)
    result = await engine.synthesize(text, params_dict)
    minio_key = storage.upload_audio(result.audio, prefix="tts", call_id=params_dict.get("call_id", ""))
    headers = {}
    if minio_key:
        headers["X-Minio-Key"] = minio_key
    return Response(content=result.audio, media_type=result.content_type, headers=headers)
