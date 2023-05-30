#!/usr/bin/env python
"""Extract a network of notable nodes and paths between them.

A node is notable if:

1. It is a high peak
2. It is the junction of 2+ trails
3. It is the junction of a trail and the road network.

This outputs a list of notable nodes and the paths between them.
"""

from collections import defaultdict
import json
from typing import Dict, List

from osm import OsmElement, OsmNode

peak_nodes: List[OsmNode] = json.load(open('data/peaks-connected.json'))['elements']

trail_elements: List[OsmElement] = json.load(open('data/trails.json'))['elements']
node_to_trails = defaultdict(list)
trail_ways = [el for el in trail_elements if el['type'] == 'way']
for el in trail_ways:
    for node in el['nodes']:
        node_to_trails[node].append(el['id'])
trail_nodes = {
    el['id']: el
    for el in trail_elements
    if el['type'] == 'node'
}

road_elements: List[OsmElement] = json.load(open('data/roads.json'))['elements']
node_to_roads = defaultdict(list)
road_ways = [el for el in road_elements if el['type'] == 'way']
for el in road_ways:
    for node in el['nodes']:
        node_to_roads[node].append(el['id'])

# 1. High peaks
notable_nodes: Dict[int, OsmElement] = {node['id']: node for node in peak_nodes}
trailhead_nodes: Dict[int, OsmElement] = {}

# 2. Junction of 2+ trails
for node_id, trails in node_to_trails.items():
    node = trail_nodes[node_id]
    if len(trails) >= 2:
        if node_id not in notable_nodes:
            notable_nodes[node_id] = node

    if node_id in node_to_roads:
        trailhead_nodes[node_id] = node

print(f'Notable nodes: {len(notable_nodes)}')
print(f'Trailhead nodes: {len(trailhead_nodes)}')

# Notable nodes: 15406
# Trailhead nodes: 2077

# Run BFS starting from the high peaks to find the relevant
# trail network.