import os
import json
import yaml
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, Form
from adapter.base import ASRResult
from adapter.config import load_asr_engine

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
    engine = load_asr_engine(config["engine"]["asr"])
    if hasattr(engine, "load_model"):
        await engine.load_model()
    logger.info(f"ASR engine loaded: {config['engine']['asr']}")
    yield


app = FastAPI(title="ASR Adapter Service", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    healthy = await engine.health_check() if engine else False
    return {"status": "ok" if healthy else "degraded"}


@app.post("/asr/recognize")
async def recognize(audio: UploadFile, params: str = Form("{}")):
    audio_bytes = await audio.read()
    result = await engine.recognize(audio_bytes, json.loads(params))
    return {"text": result.text, "confidence": result.confidence, "is_final": result.is_final}
