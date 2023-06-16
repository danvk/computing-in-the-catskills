#!/usr/bin/env python
"""Augment OSM trail with a few extra bushwhacks."""

from glob import glob
import json
from typing import List

from osm import OsmElement, OsmNode, closest_point_on_trail

files = glob('data/additional-trails/*.geojson')
print(f'Loading additional trails from {len(files)}: {files}')


trails_elements = json.load(open('data/trails.json'))['elements']

osm_elements: List[OsmElement] = (
    trails_elements + json.load(open('data/roads.json'))['elements']
)
osm_ways = [el for el in osm_elements if el['type'] == 'way']
osm_nodes = {el['id']: el for el in osm_elements if el['type'] == 'node'}


ID = 0


def nextid():
    global ID
    ID -= 1
    return ID


elements: List[OsmElement] = []

for file in files:
    fc = json.load(open(file))
    assert fc['type'] == 'FeatureCollection'
    features = fc['features']
    assert len(features) == 1
    f = features[0]
    assert f['geometry']['type'] == 'LineString'
    coords = f['geometry']['coordinates']

    # Force the trail to be connected by adding the closest nodes from other
    # trails/roads on either end.
    d, start_node = closest_point_on_trail(coords[0][:2], osm_ways, osm_nodes)
    assert d < 50

    d, end_node = closest_point_on_trail(coords[-1][:2], osm_ways, osm_nodes)
    assert d < 50, f'{coords[-1][:2]} is {d} meters from {end_node}'

    nodes: List[OsmNode] = [
        start_node,
        *[
            {'id': nextid(), 'type': 'node', 'lat': lat, 'lon': lon}
            for (lon, lat, _) in coords
        ],
        end_node,
    ]

    elements += nodes
    elements.append(
        {
            'id': nextid(),
            'type': 'way',
            'nodes': [n['id'] for n in nodes],
            'tags': {
                'highway': 'path',
                'informal': 'yes',
                **f['properties'],
            },
        }
    )

with open('data/additional-trails.json', 'w') as out:
    json.dump({'elements': elements}, out, indent=2)

with open('data/combined-trails.json', 'w') as out:
    json.dump({'elements': trails_elements + elements}, out, indent=2)
