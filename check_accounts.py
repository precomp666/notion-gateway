import json
import httpx

for fn in ['state_foldercytg_fiber_at_voidash_bond.json', 'state_radar-mxs_array_at_voidash_bond.json', 'state_static_horizon_2e9_at_voidash_bond.json']:
    print(f'\n=== {fn} ===')
    with open(f'/home/host/notion_autoreg/{fn}') as f:
        d = json.load(f)
    cookies = {ck['name']: ck['value'] for ck in d.get('cookies', [])}
    tv2 = cookies.get('token_v2')
    if not tv2:
        print('No token_v2')
        continue
    c = httpx.Client(timeout=25, trust_env=False, headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})
    r = c.post('https://app.notion.com/api/v3/getSpaces', json={}, cookies={'token_v2': tv2})
    print('getSpaces:', r.status_code)
    if r.status_code == 200:
        gs = r.json()
        if gs:
            uid = next(iter(gs))
            rec = gs[uid]
            spaces = {k: v.get('value', v) for k, v in rec.get('space', {}).items()}
            for sid, sinfo in spaces.items():
                print(f'  Space: {sid} name={sinfo.get("name")} plan={sinfo.get("plan_type")}')
                gp = c.post('https://app.notion.com/api/v3/getPublicSpaceData', json={'type': 'space-ids', 'spaceIds': [sid], 'includeCounts': False}, cookies={'token_v2': tv2})
                if gp.status_code == 200:
                    cell = gp.json()['results'][0].get('cell', '')
                    tier = gp.json()['results'][0].get('subscriptionTier', '')
                    plan_type = gp.json()['results'][0].get('planType', '')
                    print(f'    cell={cell} tier={tier} planType={plan_type}')