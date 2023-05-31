#!/usr/bin/env python
"""Run a Traveling Salesman algorithm (TSP) to find the shortest hiking distance."""

import json
from typing import List

import networkx as nx

from graph import cycle_weight, make_complete_graph
from util import splitlist

features = json.load(open('data/network.geojson'))['features']
peak_features = [f for f in features if f['properties'].get('type') == 'high-peak']
id_to_peak = {f['properties']['id']: f for f in peak_features}
id_to_trailhead = {f['properties']['id']: f for f in features if f['properties'].get('type') == 'trailhead'}

G = nx.Graph()
for f in features:
    if f['geometry']['type'] != 'LineString':
        continue
    nodes = f['properties']['nodes']
    for node in nodes[1:-1]:
        assert node not in id_to_peak and node not in id_to_trailhead
    a, b = nodes[0], nodes[-1]
    d_km = f['properties']['d_km']
    G.add_edge(a, b, weight=d_km, feature=f)


print(f'Input graph: {G.number_of_nodes()} nodes / {G.number_of_edges()} edges')
print(f'  Peaks: {len(id_to_peak)}')
print(f'  Trailheads: {len(id_to_trailhead)}')

assert not G.has_node(0)

# Add an artificial, zero-weight connection between all trailheads to simulate driving.
nodes = [*G.nodes()]

for node_id in nodes:
    if id_to_trailhead.get(node_id):
        G.add_edge(0, node_id, weight=0)

GG = make_complete_graph(G, nodes=[*id_to_peak.keys()])
print(f'Complete graph: {GG.number_of_nodes()} nodes / {GG.number_of_edges()} edges')

peak_nodes: List[int] = nx.approximation.traveling_salesman_problem(GG)

# This could yield a better result but does not:
# init_nodes: List[int] = nx.approximation.traveling_salesman_problem(GG)
# peak_nodes: List[int] = nx.approximation.simulated_annealing_tsp(GG, init_nodes)

print(peak_nodes)
for i, node in enumerate(peak_nodes):
    name = id_to_peak[node]['properties']['name']
    print(f'  {i+1}: {name} ({node})')
d_km = cycle_weight(GG, peak_nodes)
print(f'Total distance: {d_km:.2f} km')

# map this back to a list of nodes in the input graph
nodes = []
for a, b in zip(peak_nodes[:-1], peak_nodes[1:]):
    path = GG.edges[a, b]['path']
    if path[0] != a:
        path = [*path[::-1]]
    assert path[0] == a
    assert path[-1] == b
    nodes += path[:-1]

while nodes[0] != 0:
    x = nodes.pop()
    nodes = [x] + nodes
assert nodes.pop(0) == 0

print(nodes)

chunks = splitlist(nodes, 0)
for i, chunk in enumerate(chunks):
    print(f'  {i}: {chunk}')

tsp_fs = [*peak_features]
for f in tsp_fs:
    f['properties']['marker-size'] = 'small'

total_d_km = 0
for node_seq in chunks:
    tsp_fs.append(id_to_trailhead[node_seq[0]])
    tsp_fs.append(id_to_trailhead[node_seq[-1]])
    d_km = sum(
        G.edges[a, b]['weight']
        for a, b in zip(node_seq[:-1], node_seq[1:])
    )
    total_d_km += d_km
    tsp_fs.append({
        'type': 'Feature',
        'properties': {
            'nodes': node_seq,
            'd_km': d_km,
            'peaks': [
                id_to_peak[node]['properties']['name']
                for node in node_seq
                if node in id_to_peak
            ]
        },
        'geometry': {
            'type': 'MultiLineString',
            'coordinates': [
                G.edges[a, b]['feature']['geometry']['coordinates']
                for a, b in zip(node_seq[:-1], node_seq[1:])
            ]
        }
    })


with open('data/tsp.geojson', 'w') as out:
    json.dump({'type': 'FeatureCollection', 'features': tsp_fs}, out)

print(f'Total hiking distance: {total_d_km:.1f} km')
