import json
import math
import random

from osm import OsmElement
from util import haversine


(low_lat, low_lng, hi_lat, hi_lng) = (41.813, -74.652, 42.352, -73.862)

mid_lat = (low_lat + hi_lat) / 2
mid_lng = (low_lng + hi_lng) / 2

print(mid_lat, mid_lng)

for name, lat, lng in [
    ('lo', low_lat, low_lng),
    ('mid', mid_lat, mid_lng),
    ('hi', hi_lat, hi_lng),
]:
    point_one_lng_m = 1000 * haversine(lng, lat, lng + 0.1, lat)
    point_one_lat_m = 1000 * haversine(lng, lat, lng, lat + 0.1)

    print(name)
    print(point_one_lng_m)
    print(point_one_lat_m)

# The lng component varies by ~1.5% over the region
# The lat component is universal

m_per_lng = 82526.71005845172
m_per_lat = 111194.9266445589


def candidate_catskills_haversine(lon1, lat1, lon2, lat2):
    return math.sqrt(
        ((lon2 - lon1) * m_per_lng) ** 2 + ((lat2 - lat1) * m_per_lat) ** 2
    )


parking_els: list[OsmElement] = json.load(open('data/parking.json'))['elements']
parking_nodes = [el for el in parking_els if el['type'] == 'node']

# Usually within 0.3%
for a, b in zip(
    random.choices(parking_nodes, k=40), random.choices(parking_nodes, k=40)
):
    lat1 = a['lat']
    lng1 = a['lon']
    lat2 = b['lat']
    lng2 = b['lon']

    d_true = 1000 * haversine(lng1, lat1, lng2, lat2)
    d_approx = candidate_catskills_haversine(lng1, lat1, lng2, lat2)
    delta = abs(d_true - d_approx)

    print(f'{d_true:.0f} vs {d_approx:.0f} ∆={delta:.0f} {delta/d_true*100:.1f}%')
