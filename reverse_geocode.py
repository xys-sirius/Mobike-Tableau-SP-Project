import requests
import time
import sys

coords = [
    (1, 121.3565, 31.1875, '闵行区'),
    (2, 121.4301, 31.3269, '杨浦区（高校区）'),
    (3, 121.4778, 31.2705, '静安寺CBD'),
    (4, 121.5396, 31.2738, '浦东新区（商务区）'),
    (5, 121.4161, 31.1428, '徐汇区南'),
    (6, 121.4538, 31.2086, '徐汇区（住宅区）'),
    (7, 121.3375, 31.2639, '长宁区西'),
    (8, 121.5085, 31.3175, '虹口区'),
    (9, 121.5321, 31.1811, '浦东南'),
    (10, 121.4105, 31.2594, '中山公园'),
]

print('聚类  | 经度        | 纬度       | 论文原称           | API实际查询结果')
print('-' * 90)
sys.stdout.flush()

for cid, lon, lat, old_name in coords:
    url = f'https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=12&language=zh'
    headers = {'User-Agent': 'PaperGeocodeCheck/1.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        data = resp.json()
        address = data.get('address', {})
        district = address.get('district', address.get('city_district', ''))
        city = address.get('city', '')
        suburb = address.get('suburb', '')
        county = address.get('county', '')
        display_name = data.get('display_name', 'N/A')
        
        # 优先使用 district
        short = district or suburb or county or city
        if not short:
            short = display_name[:80]
        
        print(f'Cluster {cid:2d} | {lon:10.4f} | {lat:9.4f} | {old_name:<18s} | {short}')
        print(f'         Full: {display_name[:120]}')
        sys.stdout.flush()
        time.sleep(1.2)
    except Exception as e:
        print(f'Cluster {cid:2d} | {lon:10.4f} | {lat:9.4f} | {old_name:<18s} | ERROR: {e}')
        sys.stdout.flush()