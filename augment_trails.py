#!/usr/bin/env python
"""Augment OSM trail with a few extra bushwhacks.

This is only relevant for the Catskills -- for the ADKs, we stay on-trail.
"""

from glob import glob
import json
from typing import List

from osm import OsmElement, OsmNode, closest_point_on_trail

files = glob('data/catskills/additional-trails/*.geojson')
print(f'Loading additional trails from {len(files)}: {files}')


trails_elements = json.load(open('data/catskills/trails.json'))['elements']

osm_elements: List[OsmElement] = (
    trails_elements + json.load(open('data/catskills/roads.json'))['elements']
)
osm_ways = [el for el in osm_elements if el['type'] == 'way']
osm_nodes = {el['id']: el for el in osm_elements if el['type'] == 'node'}


ID = 0


def nextid():
    global ID
    ID -= 1
    return ID


elements: list[OsmElement] = []
detached_nodes: set[str] = set()

for file in files:
    print(f'Adding {file}...')
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
    if d >= 50:
        print(f'Warning: {coords[0][:2]} is {d} meters from {start_node} for {file}')
        start_node = None

    d, end_node = closest_point_on_trail(coords[-1][:2], osm_ways, osm_nodes)
    if d >= 50:
        print(f'Warning: {coords[-1][:2]} is {d} meters from {end_node} for {file}')
        end_node = None

    assert start_node or end_node

    nodes: List[OsmNode] = [
        *([start_node] if start_node else []),
        *[
            {'id': nextid(), 'type': 'node', 'lat': lat, 'lon': lon}
            for (lon, lat) in (
                c[:2] for c in coords
            )  # drop elevation, we'll re-add it later
        ],
        *([end_node] if end_node else []),
    ]

    elements += nodes
    new_way = {
        'id': nextid(),
        'type': 'way',
        'nodes': [n['id'] for n in nodes],
        'tags': {
            'highway': 'path',
            'informal': 'yes',
            'source-file': file,
            **f['properties'],
        },
    }
    elements.append(new_way)

    # this allows additional trails to connect with each other
    osm_ways.append(new_way)
    for node in nodes:
        if node['id'] not in osm_nodes:
            osm_nodes[node['id']] = node

    if not start_node:
        detached_nodes.add(nodes[0]['id'])

    if not end_node:
        detached_nodes.add(nodes[-1]['id'])

print(f'Remaining detached nodes: {detached_nodes}')
for node_id in detached_nodes:
    node_ways = [
        way for way in elements if way['type'] == 'way' and node_id in way['nodes']
    ]
    assert len(node_ways) == 1
    node_way = node_ways[0]
    if (
        node_way['tags']['source-file']
        == 'data/catskills/additional-trails/dry-brook-true-summit.geojson'
    ):
        # this is just a spur to the true summit; it can be detached.
        continue
    way_id = node_way['id']
    node = osm_nodes[node_id]
    is_start_node = node_id == node_way['nodes'][0]
    is_end_node = node_id == node_way['nodes'][-1]
    assert is_start_node or is_end_node
    other_ways = [way for way in osm_ways if way['id'] != way_id]
    coords = (node['lon'], node['lat'])
    d, closest_node = closest_point_on_trail(coords, other_ways, osm_nodes)
    assert d < 80, f'{coords} is {d} meters from {closest_node}'

    if is_end_node:
        node_way['nodes'].append(closest_node['id'])
    else:
        node_way['nodes'].insert(0, closest_node['id'])
    print(f'Reattached {node_id} to {closest_node["id"]} @ {d} m')

with open('data/catskills/additional-trails.json', 'w') as out:
    json.dump({'elements': elements}, out, indent=2)

with open('data/catskills/combined-trails.json', 'w') as out:
    json.dump({'elements': trails_elements + elements}, out, indent=2)
