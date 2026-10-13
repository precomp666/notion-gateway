# Notion Agent Gateway — Documentation

## Overview

This is an **OpenAI-compatible API gateway** that proxies requests to **Notion's free AI agent** (Opus 5.5, GPT-6.1 Sol, Kimi K3, Sonnet 5.5, Haiku 5.5, Gemini 3.7 Flash, Grok 4.6, DeepSeek V4, GLM 5.2/5.3 — 39 models total).

**Key features:**
- Runs locally on `http://127.0.0.1:3100/v1`
- OpenAI-compatible `/v1/chat/completions` and `/v1/models` endpoints
- Uses `curl_cffi` with Chrome TLS fingerprint to bypass Notion's `UserValidationError`
- Account pool with round-robin + cooldown (3 min on 401/403/429)
- Real streaming via Server-Sent Events (SSE)
- Supports `reasoning_effort` (low/medium/high/xhigh/max) per model
- Supports web search via `web_search: true` in request body

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Cline, Continue,                  │
│                        Hermes, openai-python, curl)             │
└────────────────────────────────┬────────────────────────────────┘
                                 │ OpenAI API format
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GATEWAY (FastAPI + Uvicorn)                  │
│  • Auth (Bearer token)                                          │
│  • Model validation (404 on unknown)                            │
│  • Round-robin account selection                                │
│  • Cooldown management                                          │
│  • SSE streaming wrapper                                        │
│  • Usage reporting (chars, Notion doesn't expose tokens)        │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Notion Agent Protocol
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NOTION AI AGENT (app.notion.com)             │
│  POST /api/v3/createAgentThread   → threadId                    │
│  POST /api/v3/getThreadTranscript → patches stream (poll)       │
│  POST /api/v3/getPublicSpaceData  → cell hint (required)        │
│  TLS fingerprint: curl_cffi impersonate="chrome"                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
notion-agent-gateway/
├── gateway_v3.py          # Main gateway (async, streaming, v3)
├── gateway_v2.py          # Legacy sync gateway
├── smoke_test.py          # 6-test validation suite
├── requirements.txt       # fastapi, uvicorn, curl_cffi, httpx
├── model_registry.json    # 39 models with efforts + disabled flags
├── pool.json              # Account pool (built from state files)
├── build_pool2.py         # Builds pool.json from Playwright states
├── farm_trial.py          # Auto-register accounts (voidash + OTP)
├── capture_model.py       # Capture model slugs from UI
├── capture_proto.py       # Capture full protocol (req/resp)
├── enrich_cell.py         # Enrich pool with cell hints
├── kill_gw.py             # Kill gateway process
├── GUIDE.md               # Full guide: reg → protocol → gateway
├── CHANGELOG.md           # v1→v2→v3 changes
├── README.md              # Quick start
└── state_*.json           # Playwright storage states (gitignored)
```
---

## Notion Agent Protocol (Reversed Oct 2026)

### 1. Create Thread + First Message
```
POST /api/v3/createAgentThread
Headers:
  notion-client-version: 23.13.20261008.1055
  x-notion-active-user-header: <user_id>
  x-notion-space-id: <space_id>
  x-notion-cell-hint: <cell>           # Required!
  x-notion-cell-hint-source: space-id-mapping
  Cookie: token_v2=<...>
Body:
  {
    "type": "personal_agent",
    "spaceId": "<space_id>",
    "threadId": "<uuid>",
    "model": "albuquerque-quinn",      # Internal slug
    "reasoningEffort": "low|medium|high|xhigh|max",
    "content": [{"type": "text", "text": [["user message"]]}],
    "browserEnabled": false,
    "clientMessageId": "<uuid>",
    "policies": {"approval_mode": "review_for_me"},
    "agentMemorySettings": {"useMemories": false, "excludeChatFromMemories": true},
    "enableSuggestedEditsTools": true,
    "createdSource": "full_page_chat"
  }
Response: 200 OK (thread created)
```

### 2. Poll Transcript (Long-poll)
```
POST /api/v3/getThreadTranscript
Headers: same as above
Body: {"threadId": "<tid>", "cursor": "0"}
Response: patches[] → op=put → entity.kind="assistant_message" → content[].text (markdown-escaped)
```

### 3. Cell Hint (Required for createAgentThread)
```
POST /api/v3/getPublicSpaceData
Body: {"type": "space-ids", "spaceIds": ["<space_id>"], "includeCounts": false}
Response: results[0].cell → "prod-space-usw2-0004" (example)
```
---

## Account Pool (pool.json)

Each account entry:
```json
{
  "email": "user@voidash.bond",
  "token_v2": "v03%3AeyJ...",
  "cookies": { ...all cookies... },
  "cell": "prod-space-usw2-0004",
  "user_id": "3f8d872b-594c-8168-bfac-0002755a4291",
  "space_id": "78384321-659d-81c5-bbfd-000336367902",
  "space_view_id": "3f884321-659d-81d3-9a0b-00067a4c532a",
  "space_name": "User's Space",
  "plan": "personal",
  "source_file": "state_user_at_voidash_bond.json"
}
```

**Plan types:**
- `personal` — Free personal plan, **AI agent works** ✅
- `team` — Free team plan, **AI agent blocked** (402 PaymentRequiredError) ❌

---

## Model Registry (model_registry.json)

39 models captured from `api/v3/getAvailableModels`:
- 36 enabled on free plan
- 3 Business-only (`disabled: true`) but work via direct slug:
  - `gpt-6-astra` → `orlando-quinn`
  - `fable-5.1` → `assam-chai`
  - `fable-5` → `acai-budino-high` (requires `reasoningEffort: "high"`)

Each model has:
- `name`: Display name
- `family`: anthropic/openai/gemini/xai/mystery
- `efforts`: Supported reasoning efforts
- `disabled`: Business-gate flag (UI only)

---

## Gateway v3 Key Fixes (vs v2)

| Issue | v2 | v3 |
|-------|-----|-----|
| Streaming | Fake (single chunk) | Real deltas via asyncio.Queue |
| Endpoint | Sync blocking | Async (threadpool for Notion I/O) |
| Usage | Fake `len//4` tokens | Honest chars + note |
| Model validation | Passthrough | 404 on unknown |
| Model efforts | Hardcoded 10 models | Auto-loaded from registry (39) |
| Cooldown | On any error | Only auth/429/403 |
| Premature stable | 2 polls (6s) | 4 polls (12-16s) or session status |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `127.0.0.1` | Bind address |
| `PORT` | `3100` | Port |
| `NOTION_GW_KEY` | `""` | API key (required if HOST ≠ 127.0.0.1) |
| `POOL_FILE` | `./pool.json` | Account pool path |
| `REGISTRY_FILE` | `./model_registry.json` | Model registry path |
| `NOTION_URL` | `https://app.notion.com` | Notion base URL |
| `NOTION_CLIENT_VERSION` | `23.13.20261008.1055` | Client version header |
| `POLL_INTERVAL` | `3` | Transcript poll interval (sec) |
| `STABLE_REQUIRED` | `4` | Stable polls before complete |

---

## Error Classification

```python
class AccountFault(Exception):      # → cooldown 300s
    # 401 Unauthorized, 403 Forbidden, 429 Rate Limited

class TransientFault(Exception):    # → retry NO cooldown
    # 400 ValidationError, 402 PaymentRequired, 500, 502, 503, timeouts
```

**Team accounts** (plan: team) return 402 `ai_usage_upgrade_required` → classified as `TransientFault` → retried on next account (no cooldown). Personal accounts work.

---

## Troubleshooting

### Gateway won't start
```bash
# Check port conflict
lsof -ti:3100 | xargs kill -9

# Check dependencies (use project venv)
/home/host/Projects/notion-agent-gateway/venv/bin/python -c "import fastapi, uvicorn, curl_cffi; print('OK')"

# Run with logs
cd /home/host/Projects/notion-agent-gateway
PORT=3100 NOTION_GW_KEY=test123 /home/host/Projects/notion-agent-gateway/venv/bin/python gateway_v3.py
```

### 402 PaymentRequiredError on chat
```
all retries failed: email@voidash.bond: http 402: PaymentRequiredError
```
**Cause:** Account is on team plan or free tier without AI access.
**Fix:** Ensure pool.json has `plan: "personal"` accounts. Run `farm_trial.py` to create more.

### 400 UserValidationError on createAgentThread
```
http 400: UserValidationError
```
**Cause:** Not using `curl_cffi` with `impersonate="chrome"`.
**Fix:** Gateway uses curl_cffi. If testing manually, use:
```python
from curl_cffi import requests as cq
r = cq.post(url, json=payload, headers=headers, cookies=cookies, impersonate="chrome")
```

### 404 Unknown model
```
{"error": {"message": "unknown model: xyz"}}
```
**Fix:** Use valid model alias from `/v1/models` or `model_registry.json`.

### Streaming not working (single chunk)
**Cause:** Notion protocol sends full message in patches; deltas only appear on long responses.
**Fix:** v3 pushes deltas as they arrive. Short responses = 1 chunk. This is protocol limitation.

### Pool exhausted / all cooling down
```
{"error": {"message": "pool exhausted / all cooling down"}}
```
**Fix:** Add more accounts via `farm_trial.py`, or wait for cooldowns to expire (3 min).

### Connection refused / health check fails
```bash
# Check if gateway is running
curl http://127.0.0.1:3100/health

# Check logs
cat /tmp/gateway.log

# Restart
pkill -f gateway_v3.py
PORT=3100 NOTION_GW_KEY=test123 /home/host/Projects/notion-agent-gateway/venv/bin/python gateway_v3.py
```

### Model slug mismatch (reasoningEffort validation)
```
ValidationError: medium not supported for model fireworks-kimi-k3
```
**Cause:** Model only supports specific efforts (Kimi K3: low, high, max).
**Fix:** Gateway v3 auto-clamps effort per model from registry. Use supported value.

---

## Adding More Accounts

```bash
cd /home/host/Projects/notion-agent-gateway

# 1. Install Playwright (once) - use project venv
/home/host/Projects/notion-agent-gateway/venv/bin/pip install playwright
/home/host/Projects/notion-agent-gateway/venv/bin/playwright install chromium

# 2. Run farm (creates N accounts)
/home/host/Projects/notion-agent-gateway/venv/bin/python farm_trial.py 5 Opus

# 3. Rebuild pool.json
/home/host/Projects/notion-agent-gateway/venv/bin/python build_pool2.py /home/host/notion_autoreg/ pool.json

# 4. Update cell hints (auto-fetches)
/home/host/Projects/notion-agent-gateway/venv/bin/python get_cells.py
# Then manually update pool.json or run update_cells.py

# 5. Gateway auto-reloads pool.json on next request
```