import requests
import json
import pandas as pd

url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
# data = requests.get(url)

data = requests.get(url).json()

with open('data/gdacs.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)