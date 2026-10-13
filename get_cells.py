import json
import httpx

with open('pool.json') as f:
    pool = json.load(f)

for acc in pool:
    if acc.get('cell'):
        print(f'{acc["email"]}: cell={acc["cell"]}')
    else:
        tv2 = acc['token_v2']
        sid = acc['space_id']
        c = httpx.Client(timeout=25, trust_env=False, headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})
        gp = c.post('https://app.notion.com/api/v3/getPublicSpaceData', json={'type': 'space-ids', 'spaceIds': [sid], 'includeCounts': False}, cookies={'token_v2': tv2})
        if gp.status_code == 200:
            cell = gp.json()['results'][0].get('cell', '')
            print(f'{acc["email"]}: cell={cell}')
        else:
            print(f'{acc["email"]}: cell=ERROR {gp.status_code}')