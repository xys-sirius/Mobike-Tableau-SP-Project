import urllib.request, json, ssl

ssl._create_default_https_context = ssl._create_unverified_context

coords = [
    (1, 121.3565, 31.1875),
    (2, 121.4301, 31.3269),
]

for cid, lon, lat in coords:
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=12&language=zh"
    req = urllib.request.Request(url, headers={"User-Agent": "PaperCheck/1.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        print(f"Cluster {cid}: ({lon}, {lat})")
        print(f"  Display: {data.get('display_name', 'N/A')}")
        addr = data.get("address", {})
        print(f"  District: {addr.get('district', '')}, Suburb: {addr.get('suburb','')}, County: {addr.get('county','')}")
    except Exception as e:
        print(f"Cluster {cid}: ERROR: {e}")