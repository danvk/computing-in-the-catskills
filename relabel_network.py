"""Make GeoJSON feature IDs smaller numbers to shrink downstream artifacts."""

import json
import sys
from collections import Counter


def run(geojson_file: str, hikes_file: str):
    features = json.load(open(geojson_file))['features']
    hikes = json.load(open(hikes_file))
    id_counts = Counter()
    for hike in hikes:
        nodes = hike[-1]
        id_counts.update(nodes)

    old_to_new_id = {id: 1 + i for i, (id, _) in enumerate(id_counts.most_common())}
    for f in features:
        p = f['properties']
        id = p.get('id')
        new_id = old_to_new_id.get(id)
        if new_id:
            p['id'] = new_id
            p['original_id'] = id
        nodes = p.get('nodes')
        if nodes:
            p['nodes'] = [old_to_new_id.get(n, n) for n in nodes]
    return {'type': 'FeatureCollection', 'features': features}


if __name__ == '__main__':
    geojson_file, hikes_file = sys.argv[1:]
    data = run(geojson_file, hikes_file)
    json.dump(data, sys.stdout)
