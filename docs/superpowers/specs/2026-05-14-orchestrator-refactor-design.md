# Agent-Orchestrator LangGraph Refactor Design

## Overview

Refactor agent-flow from an ESL-event-driven architecture to an HTTP service with a clean 7-node LangGraph pipeline. The orchestrator no longer connects directly to FreeSWITCH — it receives ASR results via HTTP and calls TTS adapter via HTTP.

## Architecture Change

**Before:** ESL event loop → event_handlers → Graph → TTS via FreeSWITCH
**After:** FastAPI HTTP service → LangGraph 7-node pipeline → TTS via HTTP

```
呼入: FreeSWITCH → UniMRCP → ASR adapter → POST /call/speech → orchestrator
呼出: orchestrator → POST /tts/synthesize_json → TTS adapter → UniMRCP → FreeSWITCH
```

## LangGraph Flow (7 Nodes)

```
① receive_asr        — 接收 ASR 文本 + minio_key
② mcp_identity       — 查询用户中心（身份/姓名/性别）
③ [条件] credit_query — 仅 marketing 查询征信
④ recall_memory      — Redis 热记忆 + PG 长期记忆
⑤ rag_retrieve       — pgvector 话术检索
⑥ llm_decide         — LLM 结构化输出
⑦ tts_synthesize     — 调用 TTS adapter，返回音频 + minio_key
```

Linear flow with one conditional branch: node ③ only executes when `biz_type == "marketing"`.

## State Definition

`CallGraphState` TypedDict:

| Field | Type | Description |
|-------|------|-------------|
| `call_id` | str | 通话唯一 ID |
| `biz_type` | str | 业务类型 (customer_service/collection/marketing) |
| `user_key` | str | 用户标识 |
| `user_input` | str | ASR 识别文本 |
| `asr_minio_key` | str | None | 呼入音频 MinIO 地址 |
| `identity` | dict | None | MCP 身份查询结果 |
| `credit_result` | dict | None | 征信查询结果（仅 marketing） |
| `memory_block` | str | 聚合记忆文本 |
| `rag_block` | str | RAG 检索文本 |
| `llm_action` | LLMAction | None | LLM 决策结果 |
| `tts_minio_key` | str | None | TTS 音频 MinIO 地址 |
| `tts_audio` | str | None | TTS 音频 base64 |
| `turn_count` | int | 当前轮次 |
| `turn_history` | list | 对话历史 |

## API Endpoint

### POST /call/speech

**Request:**
```json
{
  "call_id": "uuid-string",
  "biz_type": "marketing",
  "user_key": "phone_hash",
  "text": "ASR 识别的文本",
  "minio_key": "asr/20260514/uuid.wav"
}
```

**Response:**
```json
{
  "action": "say|ask|handoff|end",
  "text": "回复文本",
  "tts_minio_key": "tts/20260514/uuid.wav",
  "tts_audio": "base64-encoded-wav"
}
```

### GET /healthz

Returns service health status.

## Redis Conversation Context

Replace in-memory `CallStateManager` with Redis:

- Key: `cb:ctx:{call_id}`
- Value: JSON with `turn_history`, `identity`, `turn_count`, `user_key`
- TTL: 1 hour (auto-expire after call ends)
- Load before Graph invoke, save after Graph completes

## Files to Delete (16)

| File | Reason |
|------|--------|
| `fs_esl.py` | No direct FreeSWITCH connection |
| `fs_actions.py` | No direct FreeSWITCH connection |
| `event_handlers.py` | No ESL event loop |
| `call_state.py` | Replaced by Redis context |
| `compliance.py` | Compliance check removed |
| `llm_base.py` | DEPRECATED |
| `rag_retriever.py` | DEPRECATED |
| `memory/pg_facts.py` | DEPRECATED |
| `memory/pg_vector.py` | DEPRECATED |
| `storage/db_pg.py` | DEPRECATED |
| `llm_engines/` directory | DEPRECATED |
| `tests/test_llm_base.py` | Tests deprecated code |
| `tests/test_rag_retriever.py` | Tests deprecated code |
| `tests/test_prompt_builder.py` | Broken (wrong import) |
| `tests/test_event_handlers.py` | ESL removed |
| `tests/test_fs_actions.py` | ESL removed |

## Files to Keep (13)

| Module | Responsibility |
|--------|---------------|
| `main.py` | FastAPI app + lifespan initialization |
| `config.py` | pydantic-settings configuration |
| `graph_flow.py` | LangGraph 7-node pipeline |
| `mcp_client.py` | MCP user center + credit query |
| `prompt_builder.py` | Prompt assembly |
| `tts_client.py` | **NEW** — TTS adapter HTTP client |
| `llm/service.py` | LLM service (LangChain) |
| `memory/assembler.py` | Memory aggregation |
| `memory/store.py` | PG data access |
| `memory/redis_memory.py` | Redis hot memory |
| `rag/retriever.py` | RAG retrieval |
| `database.py` | DB connection |
| `db/models.py` | ORM models |
| `storage/repository.py` | Data persistence |

## Node Details

### ① receive_asr
- Input: request body (call_id, biz_type, user_key, text, minio_key)
- Action: populate state fields, load conversation context from Redis
- Output: state with user_input, asr_minio_key, turn_history from Redis

### ② mcp_identity
- Action: call `MCPClient.query_user_identity(user_key, biz_type)`
- Output: state with identity (user_id, name_masked, gender, verified)
- On failure: set identity=None, continue (non-blocking)

### ③ credit_query (conditional: only biz_type=="marketing")
- Action: call `MCPClient.query_credit_profile(user_id, user_key)`
- Output: state with credit_result
- On failure: set credit_result=None, continue (non-blocking)

### ④ recall_memory
- Action: call `MemoryAssembler.assemble(user_key, biz_type)`
- Output: state with memory_block

### ⑤ rag_retrieve
- Action: call `rag.retriever.retrieve_scripts(biz_type, user_input)`
- Output: state with rag_block

### ⑥ llm_decide
- Action: call `LLMService.chat_for_action(messages)` with structured output
- Input: system prompt + rag_block + memory_block + turn_history + user_input
- Output: state with llm_action (action, text, intent)

### ⑦ tts_synthesize
- Action: call `TTSClient.synthesize(text, call_id, biz_type)` → TTS adapter `/tts/synthesize_json`
- Output: state with tts_audio (base64) and tts_minio_key
- On failure: tts_audio=None, tts_minio_key=None (return text-only)
- After: save conversation context to Redis (increment turn_count, append to turn_history)

## main.py Structure

```python
app = FastAPI(title="Agent Orchestrator", lifespan=lifespan)

@asynccontextmanager
async def lifespan(app):
    # Initialize: DB engine, Redis, LLM service, MemoryAssembler, MCPClient, TTSClient
    yield

@app.post("/call/speech")
async def handle_speech(request: SpeechRequest):
    # 1. Load Redis context
    # 2. Build initial state
    # 3. Run graph.ainvoke(state)
    # 4. Save Redis context
    # 5. Return response

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
```
