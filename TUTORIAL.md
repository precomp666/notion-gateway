# Notion Agent Gateway — Step-by-Step Tutorial

## Prerequisites

- Linux/macOS (WSL2 on Windows works)
- Python 3.10+
- Virtual environment recommended

---

## 1. Clone & Setup

```bash
# Clone the repository
cd /home/host/Projects
git clone https://github.com/ArthurMonteiro08586/notion-agent-gateway.git
cd notion-agent-gateway

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
# Required: fastapi, uvicorn, curl_cffi, httpx
```

**Note:** `curl_cffi` is MANDATORY — plain `httpx`/`requests` gets `400 UserValidationError` due to TLS fingerprinting.

---

## 2. Create Notion Accounts (Personal Free Plans)

You need **personal free accounts** (not team plans) with AI agent access.

### Option A: Automated (farm_trial.py)

```bash
# Install Playwright (once)
pip install playwright
playwright install chromium

# Run farm - creates N accounts with Opus 5.5
# Uses voidash.bond catch-all email + OTP
python farm_trial.py 10 Opus

# This creates:
# - state_<email>.json files in /home/host/notion_autoreg/
# - farm_trial_accounts.jsonl with results
```

### Option B: Manual

1. Go to https://www.notion.so/signup
2. Use catch-all email (e.g., `yourname_<random>@voidash.bond`)
3. Complete onboarding: "For personal life" → Continue
4. Open AI Chat, select **Opus 5.5** (or any model)
5. Send test message "Hello"
6. Save storage state (Playwright: `context.storage_state(path="state_<email>.json")`)

---

## 3. Build Account Pool (pool.json)

```bash
# Set BASE path in build_pool2.py if needed (default: /home/host/notion_autoreg)
# Then run:
python build_pool2.py /home/host/notion_autoreg/ pool.json

# Output: pool.json with 10 accounts
# Each entry has: email, token_v2, cookies, cell, user_id, space_id, space_view_id, plan
```

**Important:** Only `plan: "personal"` accounts work. Team plans return 402.

---

## 4. Add Cell Hints (Required)

Each account needs a `cell` hint from `getPublicSpaceData`:

```bash
# Fetch cell hints for all accounts
python get_cells.py

# Output shows: email: cell=prod-space-usw2-0004
# Update pool.json with these values (or run update_cells.py)
```

```bash
# Quick update script
python update_cells.py
```

---

## 5. Start Gateway

**⚠️ IMPORTANT: Use the virtual environment Python!** The dependencies are installed in `venv/`, not system Python.

```bash
# Set API key and start (use venv Python)
export NOTION_GW_KEY=test123
export PORT=3100

/home/host/Projects/notion-agent-gateway/venv/bin/python gateway_v3.py

# Output:
# INFO: Uvicorn running on http://127.0.0.1:3100
```

**Run in background:**
```bash
PORT=3100 NOTION_GW_KEY=test123 /home/host/Projects/notion-agent-gateway/venv/bin/python gateway_v3.py > /tmp/gateway.log 2>&1 &
```

**Alternative: Activate venv first**
```bash
source /home/host/Projects/notion-agent-gateway/venv/bin/activate
PORT=3100 NOTION_GW_KEY=test123 python gateway_v3.py &
```
---

## 6. Verify Gateway

```bash
# Health check (no auth needed)
curl http://127.0.0.1:3100/health
# {"status":"ok"}

# List models (needs auth)
curl -H "Authorization: Bearer test123" http://127.0.0.1:3100/v1/models

# Test chat
curl -X POST http://127.0.0.1:3100/v1/chat/completions \
  -H "Authorization: Bearer test123" \
  -H "Content-Type: application/json" \
  -d '{"model":"opus-5.5","messages":[{"role":"user","content":"Hello"}],"reasoning_effort":"low"}'

# Test streaming
curl -N -X POST http://127.0.0.1:3100/v1/chat/completions \
  -H "Authorization: Bearer test123" \
  -H "Content-Type: application/json" \
  -d '{"model":"opus-5.5","messages":[{"role":"user","content":"Write a poem"}],"stream":true}'
```

---

## 7. Run Smoke Tests

```bash
NOTION_GW_KEY=test123 python smoke_test.py

# Expected output:
# [1] health OK: {'status': 'ok', 'accounts': 10, 'models': 48}
# [2] models OK: 39 unique
# [3] unknown model 404 OK
# [4] non-stream OK
# [5] stream OK
# [6] bad key 401 OK
# RESULT: ALL PASS
```

---

## 8. Connect to IDE/Agent

### Cline / Roo Code (VS Code)
```
API Provider: OpenAI Compatible
Base URL: http://127.0.0.1:3100/v1
API Key: test123
Model: opus-5.5
```

### Continue (VS Code / JetBrains)
```json
{
  "provider": "openai",
  "apiBase": "http://127.0.0.1:3100/v1",
  "apiKey": "test123",
  "model": "opus-5.5"
}
```

### Hermes / OMP
- Custom Provider → Base URL: `http://127.0.0.1:3100/v1`
- API Key: `test123`

### openai-python SDK
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:3100/v1",
    api_key="test123"
)

response = client.chat.completions.create(
    model="opus-5.5",
    messages=[{"role": "user", "content": "Hello"}],
    reasoning_effort="low"
)
```

---

## 9. Advanced Usage

### Reasoning Effort
```json
{
  "model": "opus-5.5",
  "messages": [...],
  "reasoning_effort": "high"  // low, medium, high, xhigh, max
}
```
Gateway auto-clamps to model-supported values (Kimi K3: low/high/max only).

### Web Search
```json
{
  "model": "opus-5.5",
  "messages": [...],
  "web_search": true
}
```
Enables Notion agent's browser tool. Response includes citations `[^url]`.

### Business Models (Free Access)
These are UI-disabled but work via direct slug:
```json
{"model": "gpt-6-astra"}      // GPT-6 Astra → orlando-quinn
{"model": "fable-5.1"}        // Fable 5.1 → assam-chai
{"model": "fable-5"}          // Fable 5 → acai-budino-high (effort=high)
```

---

## 10. Maintenance

### Add More Accounts
```bash
python farm_trial.py 5 Opus
python build_pool2.py /home/host/notion_autoreg/ pool.json
python get_cells.py
# Update pool.json with new cell hints
# Gateway auto-reloads on next request
```

### Check Account Health
```bash
curl http://127.0.0.1:3100/health
# {"status":"ok","accounts":10,"models":48}
```

### View Logs
```bash
cat /tmp/gateway.log
# Or if running in foreground, check terminal output
```

### Kill Gateway
```bash
pkill -f gateway_v3.py
# Or use kill_gw.py
python kill_gw.py
```

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| `402 PaymentRequiredError` | Account is team plan → use personal accounts only |
| `400 UserValidationError` | Must use `curl_cffi` with `impersonate="chrome"` |
| `Connection refused` | Gateway not running → start it |
| `Pool exhausted` | All accounts cooling down → wait 3 min or add more |
| `Unknown model` | Use valid alias from `/v1/models` |
| `Streaming = 1 chunk` | Normal for short responses (protocol limitation) |

---

## File Locations Summary

| File | Purpose |
|------|---------|
| `/home/host/Projects/notion-agent-gateway/gateway_v3.py` | Main server |
| `/home/host/Projects/notion-agent-gateway/pool.json` | Account pool (10 accounts) |
| `/home/host/Projects/notion-agent-gateway/model_registry.json` | 39 models config |
| `/home/host/notion_autoreg/state_*.json` | Playwright sessions (gitignored) |
| `/home/host/notion_autoreg/farm_trial_accounts.jsonl` | Farm results log |
| `/tmp/gateway.log` | Gateway runtime logs |

---

## Quick Reference Card

```bash
# Start gateway (use venv Python!)
PORT=3100 NOTION_GW_KEY=test123 /home/host/Projects/notion-agent-gateway/venv/bin/python gateway_v3.py &

# Test
curl -X POST http://127.0.0.1:3100/v1/chat/completions \
  -H "Authorization: Bearer test123" \
  -H "Content-Type: application/json" \
  -d '{"model":"opus-5.5","messages":[{"role":"user","content":"Hi"}]}'

# Add accounts (use venv Python!)
/home/host/Projects/notion-agent-gateway/venv/bin/python farm_trial.py 5 Opus
/home/host/Projects/notion-agent-gateway/venv/bin/python build_pool2.py /home/host/notion_autoreg/ pool.json
/home/host/Projects/notion-agent-gateway/venv/bin/python get_cells.py
/home/host/Projects/notion-agent-gateway/venv/bin/python update_cells.py

# Health
curl http://127.0.0.1:3100/health
```