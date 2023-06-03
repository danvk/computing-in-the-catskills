#!/usr/bin/env python
"""Find minimum hiking distance, requiring loop hikes."""

# Each node is a (trailhead, peak) pair, where the trailhead is where you parked your car.
# Each nodeset is (*, peak)
# Traveling from (A, X) to (B, Y) requires traveling:
# - From X to A on trails
# - From A to B by car
# - From B to Y on trails

# Plan of attack:
# ✓ Form a new graph consisting of (trailhead, peak) pairs; Trailhead nodes are left as-is.
# - Attach the artificial zero node and produce a complete graph.
# - Run GTSP over this complete graph w/ relevant nodesets.
# - Map this back to a sequence of hikes
# - Visualize

import json
from typing import List

import networkx as nx

from graph import make_complete_graph, read_hiking_graph

features = json.load(open('data/network.geojson'))['features']
G, id_to_peak, id_to_trailhead = read_hiking_graph(features)
peak_features = [f for f in features if f['properties'].get('type') == 'high-peak']

trail_g = nx.Graph()

for th_node in G.nodes():
    if G.nodes[th_node]['type'] != 'trailhead':
        continue

    lengths, paths = nx.single_source_dijkstra(G, th_node)
    for node, length in lengths.items():
        if G.nodes[node]['type'] == 'trailhead':
            continue  # we want to disallow trailhead->trailhead travel
        trail_g.add_edge(th_node, (th_node, node), weight=length, path=paths[node])

peak_nodes = [n for n in trail_g.nodes() if isinstance(n, tuple) and G.nodes[n[1]]['type'] == 'high-peak']
# 624 trailhead/peak tuples
print(f'{len(peak_nodes)} trailhead/peak tuples')

# for trailhead_id, peak_id in tuples:
#     th = id_to_trailhead[trailhead_id]
#     peak = id_to_peak[peak_id]
#     print(f'  {trailhead_id}, {peak_id} = {th["properties"].get("name")}, {peak["properties"].get("name")}')

# Add artificial zero node to connect trailheads
nodes = [*trail_g.nodes()]
for node_id in nodes:
    if id_to_trailhead.get(node_id):
        trail_g.add_edge(0, node_id, weight=0)

GG = make_complete_graph(trail_g, nodes=peak_nodes)
# Complete graph: 624 nodes / 194376 edges
print(f'Complete graph: {GG.number_of_nodes()} nodes / {GG.number_of_edges()} edges')
