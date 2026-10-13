import json
with open('pool.json') as f:
    pool = json.load(f)
for acc in pool:
    print(f'{acc["email"]}: cell={acc.get("cell", "MISSING")}')