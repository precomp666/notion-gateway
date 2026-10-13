import json

# Cell mapping from get_cells.py output
cell_map = {
    "agp9-kernel-domain@voidash.bond": "prod-space-usw2-0004",
    "event-accessmkem@voidash.bond": "prod-space-usw2-0004",
    "ji_object-folder@voidash.bond": "prod-space-usw2-0003",
    "level.vbg-align@voidash.bond": "prod-space-usw2-0004",
    "mapper_4hx.source@voidash.bond": "prod-space-usw2-0004",
    "mapper_comet7vnd@voidash.bond": "prod-space-usw2-0004",
    "nebula_u5m.memory@voidash.bond": "prod-space-usw2-0003",
    "photon_delta-kb4@voidash.bond": "prod-space-usw2-0004",
    "syntax_65tv-patch@voidash.bond": "prod-space-usw2-0003",
    "token_gjki.laser@voidash.bond": "prod-space-usw2-0003",
    "uwu-memory-patch@voidash.bond": "prod-space-usw2-0004",
}

with open('pool.json', 'r') as f:
    pool = json.load(f)

for acc in pool:
    email = acc['email']
    if email in cell_map:
        acc['cell'] = cell_map[email]
        print(f"Updated {email}: cell={cell_map[email]}")

with open('pool.json', 'w') as f:
    json.dump(pool, f, indent=1)

print("Done!")