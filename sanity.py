#!/usr/bin/env python

import json
from typing import List
from collections import defaultdict

from osm import OsmElement, OsmNode


peak_nodes: List[OsmNode] = json.load(open('data/peaks-connected.json'))['elements']
assert len(peak_nodes) == 33

node_id_to_peak = {n['id']: n for n in peak_nodes}


trail_elements: List[OsmElement] = json.load(open('data/trails.json'))['elements']
node_to_trails = defaultdict(list)
trail_ways = [el for el in trail_elements if el['type'] == 'way']
for el in trail_ways:
    for node in el['nodes']:
        node_to_trails[node].append(el['id'])
trail_nodes = {el['id']: el for el in trail_elements if el['type'] == 'node'}

# Are the start/end nodes of each trail connected to a road or another trail?
road_elements: List[OsmElement] = json.load(open('data/roads.json'))['elements']
node_to_roads = defaultdict(list)
road_ways = [el for el in road_elements if el['type'] == 'way']
for el in road_ways:
    for node in el['nodes']:
        node_to_roads[node].append(el['id'])


for el in trail_ways:
    way_id = el['id']
    start_node, end_node = el['nodes'][0], el['nodes'][-1]
    name = el.get('tags', {}).get('name')
    if not name:
        continue
    name = name or '(anonymous)'
    print(f'{name} ({way_id})')
    for label, node in [('start', start_node), ('end', end_node)]:
        ways_t = [n for n in node_to_trails[node] if n != way_id]
        ways_r = node_to_roads[node]
        print(f'  {label}: {len(ways_t)} t / {len(ways_r)} r')
        if len(ways_t) + len(ways_r) == 0:
            print('  ^^ disconnected!')
