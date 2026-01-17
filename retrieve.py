import requests
import json

url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"

res = requests.get(url)

with open('data/gdacs.json', 'w', encoding='utf-8') as f:
    json.dump(res, f, indent=2)