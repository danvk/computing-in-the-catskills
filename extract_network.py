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

from osm import OsmElement, OsmNode, dedupe_ways, find_path, is_in_catskills
from util import haversine

peak_nodes: List[OsmNode] = json.load(open('data/peaks-connected.json'))['elements']
id_to_peak_node = {
    el['id']: el
    for el in peak_nodes
}

trail_elements: List[OsmElement] = json.load(open('data/combined-trails.json'))['elements']
node_to_trails = defaultdict(list)
trail_ways_dupes = [el for el in trail_elements if el['type'] == 'way']
trail_ways = [*dedupe_ways(trail_ways_dupes)]
trail_nodes = {
    el['id']: el
    for el in trail_elements
    if el['type'] == 'node'
    # TODO: this filter could probably be applied in the trails.txt query instead.
    and is_in_catskills(el['lon'], el['lat'])
}
trail_ways = [
    way
    for way in trail_ways
    if all(node in trail_nodes for node in way['nodes'])
]
for el in trail_ways:
    for node in el['nodes']:
        node_to_trails[node].append(el['id'])
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


def pairkey(a: int, b: int) -> Tuple[int, int]:
    return (a, b) if a <= b else (b, a)

# Fill out the edges a bit:
# - extract the sequence of coordinates
# - pick the shorter one (where relevant)
# - record whether it's trail/trail or road/trail
paths: Dict[Tuple[int, int], Trail] = {}
ab: Tuple[int, int]
for a, b in peak_g.edges():
    key = pairkey(a, b)
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
    peak_g.edges[a, b]['d_km'] = best.d_km

# Repeat until convergence:
# - Remove all nodes with degree 1 that aren't peaks or trailheads
# - "Inline" all nodes with degree 2 that aren't peaks or trailheads
while True:
    any_changed = False

    nodes = [*peak_g.nodes()]
    for node_id in nodes:
        if id_to_peak_node.get(node_id) or node_to_roads.get(node_id):
            continue

        d = peak_g.degree[node_id]
        if d == 1:
            peak_g.remove_node(node_id)
            any_changed = True
        elif d == 2:
            # "inline" this node
            pass

    if not any_changed:
        break

print('After pruning:')
print(f'nodes: {peak_g.number_of_nodes()}, edges: {peak_g.number_of_edges()}')

features = []
for node_id in peak_g.nodes():
    peak_node = id_to_peak_node.get(node_id)
    if peak_node:
        features.append({
            'type': 'Feature',
            'geometry': { 'type': 'Point', 'coordinates': (peak_node['lon'], peak_node['lat'])},
            'properties': {
                'id': node_id,
                'type': 'high-peak',
                **peak_node['tags'],
                'marker-color': '#0000ff',
                'marker-size': 'large',
                'degree': peak_g.degree[node_id]
            }
        })
        continue
    trail_node = trail_nodes[node_id]
    features.append({
        'type': 'Feature',
        'geometry': { 'type': 'Point', 'coordinates': (trail_node['lon'], trail_node['lat'])},
        'properties': {
            'id': node_id,
            'type': 'trailhead' if node_to_roads.get(node_id) else 'junction',
            **trail_node.get('tags', {}),
            'marker-size': 'small',
            'marker-color':
                '#00ff00' if peak_g.degree[node_id] == 1 and not node_to_roads.get(node_id) else
                '#ff00ff' if peak_g.degree[node_id] == 2 and not node_to_roads.get(node_id) else
                '#555555' if not node_to_roads.get(node_id) else
                '#ff0000',
            'trail-ways': node_to_trails[node_id],
            'road-ways': node_to_roads.get(node_id, None),
            'degree': peak_g.degree[node_id]
        }
    })
id_to_point = {f['properties']['id']: f for f in features}

for path in paths.values():
    a, b = path.nodes[0], path.nodes[-1]
    if not peak_g.has_edge(a, b):
        continue  # must have been pruned
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


assert not peak_g.has_node(0)
nodes = [*peak_g.nodes()]
for node_id in nodes:
    if node_to_roads.get(node_id):
        peak_g.add_edge(0, node_id, d_km=0)

nodes: List[int] = nx.approximation.traveling_salesman_problem(
    peak_g, nodes=id_to_peak_node.keys(), weight='d_km', cycle=True
)

while nodes[0] != 0:
    x = nodes.pop()
    nodes = [x] + nodes
assert nodes.pop(0) == 0

chunks = []
last = 0
for node in nodes:
    if node == 0:
        last = 0
        continue

    if last == 0:
        chunks.append([node])
    elif node == last:
        continue  # not sure why this happens?
    else:
        chunks[-1].append(node)
    last = node

print(chunks)

tsp_fs = []
total_d_km = 0
for node_seq in chunks:
    tsp_fs.append(id_to_point[node_seq[0]])
    tsp_fs.append(id_to_point[node_seq[-1]])
    d_km = sum(
        paths[pairkey(a, b)].d_km
        for a, b in zip(node_seq[:-1], node_seq[1:])
    )
    total_d_km += d_km
    tsp_fs.append({
        'type': 'Feature',
        'properties': {
            'nodes': node_seq,
            'd_km': d_km
        },
        'geometry': {
            'type': 'MultiLineString',
            'coordinates': [
                paths[pairkey(a, b)].latlons
                for a, b in zip(node_seq[:-1], node_seq[1:])
            ]
        }
    })


with open('data/tsp.geojson', 'w') as out:
    json.dump({'type': 'FeatureCollection', 'features': tsp_fs}, out)

print(f'Total hiking distance: {total_d_km:.1f} km')
