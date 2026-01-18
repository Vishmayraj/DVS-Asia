import json
from collections import defaultdict

with open("data/gdacs.json", encoding="utf-8") as f:
    data = json.load(f)

# groups = defaultdict(list)
# for ftr in data["features"]:
#     ev_id = ftr["properties"]["eventid"]
#     groups[ev_id].append(ftr)

# for ev_id, feats in groups.items():
#     if len(feats) > 1:
#         base_props = {k: v for k, v in feats[0]["properties"].items() if k != "geometry"}
#         diffs = []
#         for f in feats[1:]:
#             props = {k: v for k, v in f["properties"].items() if k != "geometry"}
#             if props != base_props:
#                 diffs.append(f)
#         if not diffs:
#             print(f"✅ Event {ev_id} — identical properties, geometry only differs ({len(feats)} features)")
#         else:
#             print(f"⚠️ Event {ev_id} — some property differences found ({len(feats)} features)")

latest = {}

for f in data["features"]:
    p = f["properties"]
    ev_id = p["eventid"]
    # Keep the one with the latest modification time
    if ev_id not in latest or p["datemodified"] > latest[ev_id]["properties"]["datemodified"]:
        latest[ev_id] = f

# Now latest.values() has only the most recent feature for each eventid
filtered_features = list(latest.values())


for feature in filtered_features:
    print(feature['properties']['eventid'],feature['geometry'])


# print(f"Kept {len(filtered_features)} most recent events out of {len(data['features'])}")


# from collections import Counter
# ids = [f["properties"]["eventid"] for f in data["features"]]
# print(Counter(ids).most_common(5))
