#!/usr/bin/env python
"""Extract a network of notable nodes and paths between them.

A node is notable if:

1. It is a high peak
2. It is the junction of 2+ trails
3. It is the junction of a trail and the road network.

This outputs a list of notable nodes and the paths between them.
"""

from collections import defaultdict
from dataclasses import dataclass
import json
from typing import Dict, List, Set, Tuple, Union

import networkx as nx

from osm import OsmElement, OsmNode, dedupe_ways, find_path
from util import haversine

peak_nodes: List[OsmNode] = json.load(open('data/peaks-connected.json'))['elements']
id_to_peak_node = {
    el['id']: el
    for el in peak_nodes
}

trail_elements: List[OsmElement] = json.load(open('data/trails.json'))['elements']
node_to_trails = defaultdict(list)
trail_ways_dupes = [el for el in trail_elements if el['type'] == 'way']
trail_ways = [*dedupe_ways(trail_ways_dupes)]
for el in trail_ways:
    for node in el['nodes']:
        node_to_trails[node].append(el['id'])
trail_nodes = {
    el['id']: el
    for el in trail_elements
    if el['type'] == 'node'
}
id_to_trail_way = {way['id']: way for way in trail_ways}

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

# A path can be relevant because it connects a peak/trail, trail/trail or trail/road
# but not because it connects two roads.
connections: Dict[Tuple[int, int], List[int]] = defaultdict(list)  # (node, node) -> way[]; nodes are sorted
for way in trail_ways:
    id = way['id']
    nodes = [node for node in way['nodes'] if node in notable_nodes or node in trailhead_nodes]
    if not nodes:
        continue

    for a, b in zip(nodes[:-1], nodes[1:]):
        # At least one node must be notable; they can't both be trailheads.
        if a in notable_nodes or b in notable_nodes:
            key = (a, b) if a < b else (b, a)
            connections[key].append(id)

print(f'Connections: {len(connections)}')
for (a, b), ways in connections.items():
    if len(ways) > 1:
        print(f'Many paths from {a} -> {b}: {ways}')

# Run BFS starting from the high peaks to find the relevant trail network.
# This should prune out most nodes and paths.
g = nx.Graph(connections.keys())
print(f'nodes: {g.number_of_nodes()}, edges: {g.number_of_edges()}')
peaks_component: Set[int] = set()  # set of nodes connected to high peaks
for node in peak_nodes:
    id = node['id']
    if id in peaks_component:
        continue
    if id not in g:
        name = node['tags']['name']
        print(f'Node {id} / {name} is not connected')
        continue
    peaks_component.update(nx.node_connected_component(g, id))

print(f'Nodes connected to a high peak: {len(peaks_component)}')
peak_g: nx.Graph = g.subgraph(peaks_component).copy()
print(f'nodes: {peak_g.number_of_nodes()}, edges: {peak_g.number_of_edges()}')


@dataclass
class Trail:
    d_km: float
    way: int
    nodes: List[int]
    latlons: List[Tuple[float, float]]


# Fill out the edges a bit:
# - extract the sequence of coordinates
# - pick the shorter one (where relevant)
# - record whether it's trail/trail or road/trail
paths: Dict[Tuple[int, int], Trail] = {}
ab: Tuple[int, int]
for a, b in peak_g.edges():
    key = (a, b) if a < b else (b, a)
    way_ids = connections[key]
    best: Union[Trail, None] = None
    for way_id in way_ids:
        # Find the subsequence of nodes and calculate a distance
        way = id_to_trail_way[way_id]
        nodes = find_path(way, a, b)
        assert nodes, f'{way}: [{a}, {b}]'
        latlons = []
        for node_id in nodes:
            n = trail_nodes[node_id]
            latlons.append((n['lon'], n['lat']))
        d_km = sum(
            haversine(
                alon, alat, blon, blat
            )
            for (alon, alat), (blon, blat) in zip(latlons[:-1], latlons[1:])
        )
        if not best or d_km < best.d_km:
            best = Trail(
                d_km=d_km,
                way=way_id,
                nodes=nodes,
                latlons=latlons,
            )
    assert key not in paths
    assert best
    paths[key] = best


features = []
for node_id in peaks_component:
    peak_node = id_to_peak_node.get(node_id)
    if peak_node:
        features.append({
            'type': 'Feature',
            'geometry': { 'type': 'Point', 'coordinates': (peak_node['lon'], peak_node['lat'])},
            'properties': {
                'id': node_id,
                **peak_node['tags'],
                'marker-color': '#0000ff',
                'marker-size': 'large',
            }
        })
        continue
    trail_node = trail_nodes[node_id]
    features.append({
        'type': 'Feature',
        'geometry': { 'type': 'Point', 'coordinates': (trail_node['lon'], trail_node['lat'])},
        'properties': {
            'id': node_id,
            **trail_node.get('tags', {}),
            'marker-size': 'small',
            'trail-ways': node_to_trails[node_id],
            'road-ways': node_to_roads.get(node_id, None)
        }
    })

for path in paths.values():
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates': path.latlons
        },
        'properties': {
            'id': path.way,
            'd_km': path.d_km,
            **id_to_trail_way[path.way].get('tags', {}),
            'nodes': path.nodes,
            'stroke': '#555555',
            'stroke-width': 2,
            'stroke-opacity': 1
        }
    })

with open('data/network.geojson', 'w') as out:
    json.dump({'type': 'FeatureCollection', 'features': features}, out)
