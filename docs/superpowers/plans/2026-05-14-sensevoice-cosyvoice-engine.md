# SenseVoice ASR + CosyVoice TTS Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SenseVoice ASR and CosyVoice TTS as new pluggable engines in the existing mrcp-asr and mrcp-tts adapter services, calling external model inference servers via HTTP API.

**Architecture:** Each new engine implements the existing ABC (ASREngine/TTSEngine), uses httpx AsyncClient to call FunASR Server / CosyVoice Server, and exports `Engine` alias for the reflection loader. VibeVoice engines remain untouched.

**Tech Stack:** Python 3.10+, FastAPI, httpx (async HTTP client), pytest, pytest-asyncio

---

## File Structure

### mrcp-asr (SenseVoice)

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `mrcp-asr/requirements.txt` | Python dependencies (httpx added) |
| Create | `mrcp-asr/adapter/engines/sensevoice/__init__.py` | Package marker |
| Create | `mrcp-asr/adapter/engines/sensevoice/engine.py` | SenseVoiceASREngine implementation |
| Create | `mrcp-asr/tests/engines/sensevoice/__init__.py` | Test package marker |
| Create | `mrcp-asr/tests/engines/sensevoice/test_engine.py` | Engine unit tests |
| Create | `mrcp-asr/deploy/sensevoice-asr.service` | Systemd service file |
| Modify | `mrcp-asr/adapter/config.yaml` | Switch engine to `sensevoice` |

### mrcp-tts (CosyVoice)

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `mrcp-tts/requirements.txt` | Python dependencies (httpx added) |
| Create | `mrcp-tts/adapter/engines/cosyvoice/__init__.py` | Package marker |
| Create | `mrcp-tts/adapter/engines/cosyvoice/engine.py` | CosyVoiceTTSEngine implementation |
| Create | `mrcp-tts/tests/engines/cosyvoice/__init__.py` | Test package marker |
| Create | `mrcp-tts/tests/engines/cosyvoice/test_engine.py` | Engine unit tests |
| Create | `mrcp-tts/deploy/cosyvoice-tts.service` | Systemd service file |
| Modify | `mrcp-tts/adapter/config.yaml` | Switch engine to `cosyvoice` |

---

## Task 1: SenseVoice ASR — Failing Tests

**Files:**
- Create: `mrcp-asr/tests/engines/sensevoice/__init__.py`
- Create: `mrcp-asr/tests/engines/sensevoice/test_engine.py`

- [ ] **Step 1: Create test package marker**

Create `mrcp-asr/tests/engines/sensevoice/__init__.py`:
```python
```
(empty file)

- [ ] **Step 2: Write the failing test file**

Create `mrcp-asr/tests/engines/sensevoice/test_engine.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from adapter.base import ASREngine, ASRResult
from adapter.engines.sensevoice.engine import SenseVoiceASREngine


@pytest.fixture
def engine():
    return SenseVoiceASREngine()


def test_engine_inherits_base():
    eng = SenseVoiceASREngine()
    assert isinstance(eng, ASREngine)


@pytest.mark.asyncio
async def test_health_check_success(engine):
    with patch("adapter.engines.sensevoice.engine.httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await engine.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(engine):
    with patch("adapter.engines.sensevoice.engine.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await engine.health_check()
        assert result is False


@pytest.mark.asyncio
async def test_recognize_success(engine):
    with patch("adapter.engines.sensevoice.engine.httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"text": "你好世界", "confidence": 0.95}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await engine.recognize(b"fake_audio_bytes", {"language": "zh"})
        assert isinstance(result, ASRResult)
        assert result.text == "你好世界"
        assert result.confidence == 0.95
        assert result.is_final is True


@pytest.mark.asyncio
async def test_recognize_server_error(engine):
    with patch("adapter.engines.sensevoice.engine.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("server error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="SenseVoice recognition failed"):
            await engine.recognize(b"fake_audio_bytes", {})


@pytest.mark.asyncio
async def test_recognize_semaphore_limits_concurrency(engine):
    engine._semaphore = AsyncMock()
    engine._semaphore._value = 2
    engine._semaphore.__aenter__ = AsyncMock(return_value=None)
    engine._semaphore.__aexit__ = AsyncMock(return_value=False)

    with patch("adapter.engines.sensevoice.engine.httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"text": "", "confidence": 0.0}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await engine.recognize(b"audio", {})
        engine._semaphore.__aenter__.assert_called_once()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-asr && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-asr python -m pytest tests/engines/sensevoice/test_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'adapter.engines.sensevoice.engine'`

- [ ] **Step 4: Commit failing tests**

```bash
git add mrcp-asr/tests/engines/sensevoice/__init__.py mrcp-asr/tests/engines/sensevoice/test_engine.py
git commit -m "test(asr): add SenseVoice engine failing tests"
```

---

## Task 2: SenseVoice ASR — Engine Implementation

**Files:**
- Create: `mrcp-asr/requirements.txt`
- Create: `mrcp-asr/adapter/engines/sensevoice/__init__.py`
- Create: `mrcp-asr/adapter/engines/sensevoice/engine.py`

- [ ] **Step 1: Create requirements.txt**

Create `mrcp-asr/requirements.txt`:
```
fastapi>=0.104.0
uvicorn>=0.24.0
pyyaml>=6.0
httpx>=0.25.0
```

- [ ] **Step 2: Create engine package marker**

Create `mrcp-asr/adapter/engines/sensevoice/__init__.py`:
```python
```
(empty file)

- [ ] **Step 3: Implement SenseVoiceASREngine**

Create `mrcp-asr/adapter/engines/sensevoice/engine.py`:
```python
import asyncio
import logging
import os

import httpx

from adapter.base import ASREngine, ASRResult

logger = logging.getLogger(__name__)

SENSEVOICE_API_URL = os.environ.get("SENSEVOICE_API_URL", "http://127.0.0.1:10095")
SENSEVOICE_TIMEOUT = int(os.environ.get("SENSEVOICE_TIMEOUT", "30"))
SENSEVOICE_LANGUAGE = os.environ.get("SENSEVOICE_LANGUAGE", "zh")
SENSEVOICE_MAX_CONCURRENT = int(os.environ.get("SENSEVOICE_MAX_CONCURRENT", "50"))


class SenseVoiceASREngine(ASREngine):
    def __init__(self):
        self._api_url = SENSEVOICE_API_URL
        self._timeout = SENSEVOICE_TIMEOUT
        self._language = SENSEVOICE_LANGUAGE
        self._semaphore = asyncio.Semaphore(SENSEVOICE_MAX_CONCURRENT)

    async def recognize(self, audio_stream: bytes, params: dict) -> ASRResult:
        async with self._semaphore:
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{self._api_url}/asr",
                        files={"audio": ("audio.wav", audio_stream, "audio/wav")},
                        data={"language": params.get("language", self._language)},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return ASRResult(
                        text=data.get("text", ""),
                        confidence=data.get("confidence", 0.0),
                        is_final=True,
                    )
            except Exception as e:
                logger.error(f"SenseVoice recognition failed: {e}")
                raise RuntimeError(f"SenseVoice recognition failed: {e}") from e

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._api_url}/health")
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"SenseVoice health check failed: {e}")
            return False


Engine = SenseVoiceASREngine
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-asr && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-asr python -m pytest tests/engines/sensevoice/test_engine.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Run full ASR test suite to verify no regressions**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-asr && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-asr python -m pytest tests/ -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 6: Commit**

```bash
git add mrcp-asr/requirements.txt mrcp-asr/adapter/engines/sensevoice/__init__.py mrcp-asr/adapter/engines/sensevoice/engine.py
git commit -m "feat(asr): add SenseVoice engine calling FunASR Server"
```

---

## Task 3: SenseVoice ASR — Config and Deployment

**Files:**
- Modify: `mrcp-asr/adapter/config.yaml`
- Create: `mrcp-asr/deploy/sensevoice-asr.service`

- [ ] **Step 1: Update config.yaml to use sensevoice**

Modify `mrcp-asr/adapter/config.yaml`:
```yaml
engine:
  asr: sensevoice
```

- [ ] **Step 2: Create systemd service file**

Create `mrcp-asr/deploy/sensevoice-asr.service`:
```ini
[Unit]
Description=SenseVoice ASR Adapter Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/mrcp-asr/adapter
ExecStart=/opt/mrcp-asr/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5
Environment=PYTHONPATH=/opt/mrcp-asr
Environment=SENSEVOICE_API_URL=http://127.0.0.1:10095

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Run full test suite to verify config change works**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-asr && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-asr python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add mrcp-asr/adapter/config.yaml mrcp-asr/deploy/sensevoice-asr.service
git commit -m "feat(asr): switch config to SenseVoice, add systemd service"
```

---

## Task 4: CosyVoice TTS — Failing Tests

**Files:**
- Create: `mrcp-tts/tests/engines/cosyvoice/__init__.py`
- Create: `mrcp-tts/tests/engines/cosyvoice/test_engine.py`

- [ ] **Step 1: Create test package marker**

Create `mrcp-tts/tests/engines/cosyvoice/__init__.py`:
```python
```
(empty file)

- [ ] **Step 2: Write the failing test file**

Create `mrcp-tts/tests/engines/cosyvoice/test_engine.py`:
```python
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from adapter.base import TTSEngine, TTSResult
from adapter.engines.cosyvoice.engine import CosyVoiceTTSEngine


@pytest.fixture
def engine():
    return CosyVoiceTTSEngine()


def test_engine_inherits_base():
    eng = CosyVoiceTTSEngine()
    assert isinstance(eng, TTSEngine)


def test_biz_type_profiles():
    from adapter.engines.cosyvoice.engine import BIZ_TYPE_PROFILES
    assert "customer_service" in BIZ_TYPE_PROFILES
    assert "collection" in BIZ_TYPE_PROFILES
    assert "marketing" in BIZ_TYPE_PROFILES
    for profile in BIZ_TYPE_PROFILES.values():
        assert "voice_id" in profile
        assert "speed" in profile


def test_get_profile_default(engine):
    profile = engine._get_profile({})
    assert profile["voice_id"] == "中文女"


def test_get_profile_collection(engine):
    profile = engine._get_profile({"biz_type": "collection"})
    assert profile["voice_id"] == "中文男"


def test_get_profile_unknown_biz_type(engine):
    profile = engine._get_profile({"biz_type": "unknown"})
    assert profile["voice_id"] == "中文女"


@pytest.mark.asyncio
async def test_health_check_success(engine):
    with patch("adapter.engines.cosyvoice.engine.httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await engine.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(engine):
    with patch("adapter.engines.cosyvoice.engine.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await engine.health_check()
        assert result is False


@pytest.mark.asyncio
async def test_synthesize_cache_miss(engine, tmp_path):
    engine._cache_dir = str(tmp_path)

    with patch("adapter.engines.cosyvoice.engine.httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"fake_wav_audio_bytes"
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await engine.synthesize("你好", {"biz_type": "customer_service"})
        assert isinstance(result, TTSResult)
        assert result.audio == b"fake_wav_audio_bytes"
        assert result.content_type == "audio/wav"


@pytest.mark.asyncio
async def test_synthesize_cache_hit(engine, tmp_path):
    engine._cache_dir = str(tmp_path)

    with patch("adapter.engines.cosyvoice.engine.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        profile = engine._get_profile({"biz_type": "customer_service"})
        cache_key = engine._cache_key("你好", profile)
        cache_path = engine._cache_path("customer_service", cache_key)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "wb") as f:
            f.write(b"cached_audio_bytes")

        result = await engine.synthesize("你好", {"biz_type": "customer_service"})
        assert result.audio == b"cached_audio_bytes"
        mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_synthesize_server_error(engine, tmp_path):
    engine._cache_dir = str(tmp_path)

    with patch("adapter.engines.cosyvoice.engine.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("server error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="CosyVoice synthesis failed"):
            await engine.synthesize("你好", {"biz_type": "customer_service"})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-tts && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-tts python -m pytest tests/engines/cosyvoice/test_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'adapter.engines.cosyvoice.engine'`

- [ ] **Step 4: Commit failing tests**

```bash
git add mrcp-tts/tests/engines/cosyvoice/__init__.py mrcp-tts/tests/engines/cosyvoice/test_engine.py
git commit -m "test(tts): add CosyVoice engine failing tests"
```

---

## Task 5: CosyVoice TTS — Engine Implementation

**Files:**
- Create: `mrcp-tts/requirements.txt`
- Create: `mrcp-tts/adapter/engines/cosyvoice/__init__.py`
- Create: `mrcp-tts/adapter/engines/cosyvoice/engine.py`

- [ ] **Step 1: Create requirements.txt**

Create `mrcp-tts/requirements.txt`:
```
fastapi>=0.104.0
uvicorn>=0.24.0
pyyaml>=6.0
httpx>=0.25.0
```

- [ ] **Step 2: Create engine package marker**

Create `mrcp-tts/adapter/engines/cosyvoice/__init__.py`:
```python
```
(empty file)

- [ ] **Step 3: Implement CosyVoiceTTSEngine**

Create `mrcp-tts/adapter/engines/cosyvoice/engine.py`:
```python
import asyncio
import hashlib
import logging
import os

import httpx

from adapter.base import TTSEngine, TTSResult

logger = logging.getLogger(__name__)

COSYVOICE_API_URL = os.environ.get("COSYVOICE_API_URL", "http://127.0.0.1:10096")
COSYVOICE_TIMEOUT = int(os.environ.get("COSYVOICE_TIMEOUT", "30"))
COSYVOICE_MAX_CONCURRENT = int(os.environ.get("COSYVOICE_MAX_CONCURRENT", "30"))

BIZ_TYPE_PROFILES = {
    "customer_service": {"voice_id": "中文女", "speed": 0, "volume": 0, "pitch": 0},
    "collection": {"voice_id": "中文男", "speed": -1, "volume": 1, "pitch": -1},
    "marketing": {"voice_id": "中文女", "speed": 1, "volume": 0, "pitch": 1},
}

DEFAULT_PROFILE = BIZ_TYPE_PROFILES["customer_service"]


class CosyVoiceTTSEngine(TTSEngine):
    def __init__(self):
        self._api_url = COSYVOICE_API_URL
        self._timeout = COSYVOICE_TIMEOUT
        self._cache_dir = "/data/tts_cache"
        self._semaphore = asyncio.Semaphore(COSYVOICE_MAX_CONCURRENT)

    def _get_profile(self, params: dict) -> dict:
        biz_type = params.get("biz_type", "customer_service")
        return BIZ_TYPE_PROFILES.get(biz_type, DEFAULT_PROFILE)

    def _cache_key(self, text: str, profile: dict) -> str:
        raw = f"{profile['voice_id']}:{text}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cache_path(self, biz_type: str, key: str) -> str:
        return os.path.join(self._cache_dir, biz_type, f"{key}.wav")

    async def synthesize(self, text: str, params: dict) -> TTSResult:
        async with self._semaphore:
            profile = self._get_profile(params)
            biz_type = params.get("biz_type", "customer_service")
            cache_path = self._cache_path(biz_type, self._cache_key(text, profile))

            if os.path.exists(cache_path):
                with open(cache_path, "rb") as f:
                    return TTSResult(audio=f.read())

            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{self._api_url}/tts",
                        json={
                            "text": text,
                            "speaker_id": profile["voice_id"],
                            "speed": profile["speed"],
                            "volume": profile["volume"],
                            "pitch": profile["pitch"],
                        },
                    )
                    resp.raise_for_status()
                    audio = resp.content

                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, "wb") as f:
                    f.write(audio)

                return TTSResult(audio=audio)
            except Exception as e:
                logger.error(f"CosyVoice synthesis failed: {e}")
                raise RuntimeError(f"CosyVoice synthesis failed: {e}") from e

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._api_url}/health")
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"CosyVoice health check failed: {e}")
            return False


Engine = CosyVoiceTTSEngine
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-tts && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-tts python -m pytest tests/engines/cosyvoice/test_engine.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Run full TTS test suite to verify no regressions**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-tts && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-tts python -m pytest tests/ -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 6: Commit**

```bash
git add mrcp-tts/requirements.txt mrcp-tts/adapter/engines/cosyvoice/__init__.py mrcp-tts/adapter/engines/cosyvoice/engine.py
git commit -m "feat(tts): add CosyVoice engine with cache and business type profiles"
```

---

## Task 6: CosyVoice TTS — Config and Deployment

**Files:**
- Modify: `mrcp-tts/adapter/config.yaml`
- Create: `mrcp-tts/deploy/cosyvoice-tts.service`

- [ ] **Step 1: Update config.yaml to use cosyvoice**

Modify `mrcp-tts/adapter/config.yaml`:
```yaml
engine:
  tts: cosyvoice
```

- [ ] **Step 2: Create systemd service file**

Create `mrcp-tts/deploy/cosyvoice-tts.service`:
```ini
[Unit]
Description=CosyVoice TTS Adapter Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/mrcp-tts/adapter
ExecStart=/opt/mrcp-tts/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8081
Restart=always
RestartSec=5
Environment=PYTHONPATH=/opt/mrcp-tts
Environment=COSYVOICE_API_URL=http://127.0.0.1:10096

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Run full test suite to verify config change works**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-tts && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-tts python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add mrcp-tts/adapter/config.yaml mrcp-tts/deploy/cosyvoice-tts.service
git commit -m "feat(tts): switch config to CosyVoice, add systemd service"
```

---

## Task 7: Final Verification

- [ ] **Step 1: Run full mrcp-asr test suite**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-asr && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-asr python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run full mrcp-tts test suite**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-tts && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-tts python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Verify config loads SenseVoice engine correctly**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-asr && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-asr python -c "from adapter.config import load_asr_engine; e = load_asr_engine('sensevoice'); print(type(e).__name__)"`
Expected: `SenseVoiceASREngine`

- [ ] **Step 4: Verify config loads CosyVoice engine correctly**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-tts && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-tts python -c "from adapter.config import load_tts_engine; e = load_tts_engine('cosyvoice'); print(type(e).__name__)"`
Expected: `CosyVoiceTTSEngine`

- [ ] **Step 5: Verify VibeVoice engines still load (coexistence)**

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-asr && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-asr python -c "from adapter.config import load_asr_engine; e = load_asr_engine('vibevoice'); print(type(e).__name__)"`
Expected: `VibeVoiceASREngine`

Run: `cd /Users/lindaw/Documents/aiphone/mrcp-tts && PYTHONPATH=/Users/lindaw/Documents/aiphone/mrcp-tts python -c "from adapter.config import load_tts_engine; e = load_tts_engine('vibevoice'); print(type(e).__name__)"`
Expected: `VibeVoiceTTSEngine`
