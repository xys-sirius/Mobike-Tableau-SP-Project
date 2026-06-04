import urllib.request, json, ssl

ssl._create_default_https_context = ssl._create_unverified_context

lat, lon = 31.2594, 121.4105

# Query a small bounding box around the point to see OSM features
bbox = f"{lon-0.005},{lat-0.005},{lon+0.005},{lat+0.005}"
url = f"https://overpass-api.de/api/interpreter"
query = f"""
[out:json];
(
  way["landuse"="residential"](around:1000,{lat},{lon});
  way["landuse"](around:1000,{lat},{lon});
  relation["landuse"](around:1000,{lat},{lon});
);
out tags center;
"""

req = urllib.request.Request(url, data=query.encode(), headers={"User-Agent": "PaperCheck/1.0"})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    for elem in data.get("elements", []):
        tags = elem.get("tags", {})
        center = elem.get("center", {})
        print(f"Type: {elem['type']}, Landuse: {tags.get('landuse','N/A')}, Name: {tags.get('name','N/A')}")
        print(f"  Center: {center.get('lat')}, {center.get('lon')}")
        print(f"  Tags: {json.dumps(tags, ensure_ascii=False)}")
        print()
    print(f"Total elements found: {len(data.get('elements', []))}")
except Exception as e:
    print(f"ERROR: {e}")