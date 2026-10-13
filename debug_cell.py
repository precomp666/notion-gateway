import json
import httpx
import uuid
from curl_cffi import requests as cq

with open('pool.json') as f:
    pool = json.load(f)

acc = pool[0]
tv2 = acc['token_v2']
sid = acc['space_id']

c = httpx.Client(timeout=25, trust_env=False, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Content-Type': 'application/json'
})

# Try getPublicSpaceData for cell hint
gp = c.post('https://app.notion.com/api/v3/getPublicSpaceData', 
            json={'type': 'space-ids', 'spaceIds': [sid], 'includeCounts': False}, 
            cookies={'token_v2': tv2})
print('getPublicSpaceData:', gp.status_code)
if gp.status_code == 200:
    print(json.dumps(gp.json(), indent=2))
else:
    print(gp.text)

# Test with exact gateway payload
NOTION_URL = "https://app.notion.com"
CLIENT_VERSION = "23.13.20261008.1055"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"

tid = str(uuid.uuid4())
payload = {
    "type": "personal_agent",
    "spaceId": sid,
    "threadId": tid,
    "enableSuggestedEditsTools": True,
    "model": "albuquerque-quinn",
    "reasoningEffort": "low",
    "createdSource": "full_page_chat",
    "content": [{"type": "text", "text": [["Hello"]]}],
    "policies": {"approval_mode": "review_for_me"},
    "agentMemorySettings": {"useMemories": False, "excludeChatFromMemories": True},
    "browserEnabled": False,
    "clientMessageId": str(uuid.uuid4()),
}

headers = {
    "User-Agent": UA,
    "Content-Type": "application/json",
    "notion-client-version": CLIENT_VERSION,
    "notion-audit-log-platform": "web",
    "x-notion-active-user-header": acc['user_id'],
    "x-notion-space-id": acc['space_id'],
    "x-notion-cell-hint-source": "space-id-mapping",
    "x-notion-cell-hint": acc.get('cell', ''),
    "Origin": NOTION_URL,
    "Referer": f"{NOTION_URL}/chat",
}

s = cq.Session(impersonate="chrome", timeout=45)
cookies = dict(acc.get("cookies") or {})
if not cookies and acc.get("token_v2"):
    cookies = {"token_v2": acc["token_v2"]}

r = s.post(f'{NOTION_URL}/api/v3/createAgentThread', json=payload, headers=headers, cookies=cookies)
print('\ncreateAgentThread:', r.status_code)
print(r.text[:1000])

# Also test without the extra headers that might cause issues
print("\n--- Testing with minimal headers ---")
headers_minimal = {
    "User-Agent": UA,
    "Content-Type": "application/json",
    "notion-client-version": CLIENT_VERSION,
    "x-notion-active-user-header": acc['user_id'],
    "x-notion-space-id": acc['space_id'],
    "x-notion-cell-hint-source": "space-id-mapping",
    "x-notion-cell-hint": acc.get('cell', ''),
}

s2 = cq.Session(impersonate="chrome", timeout=45)
r2 = s2.post(f'{NOTION_URL}/api/v3/createAgentThread', json=payload, headers=headers_minimal, cookies=cookies)
print('createAgentThread (minimal):', r2.status_code)
print(r2.text[:1000])