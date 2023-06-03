#!/usr/bin/env python
"""Find minimum hiking distance, requiring loop hikes."""

# Each node is a (trailhead, peak) pair, where the trailhead is where you parked your car.
# Each nodeset is (*, peak)
# Traveling from (A, X) to (B, Y) requires traveling:
# - From X to A on trails
# - From A to B by car
# - From B to Y on trails

# Plan of attack:
# - Form a new graph consisting of (trailhead, peak) pairs; Trailhead nodes are left as-is.
# - Attach the artificial zero node and produce a complete graph.
# - Run GTSP over this complete graph w/ relevant nodesets.
# - Map this back to a sequence of hikes
# - Visualize

import json
from typing import List

import networkx as nx

from graph import read_hiking_graph

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

tuples = [n for n in trail_g.nodes() if isinstance(n, tuple) and G.nodes[n[1]]['type'] == 'high-peak']
# 624 trailhead/peak tuples
print(f'{len(tuples)} trailhead/peak tuples')

# for trailhead_id, peak_id in tuples:
#     th = id_to_trailhead[trailhead_id]
#     peak = id_to_peak[peak_id]
#     print(f'  {trailhead_id}, {peak_id} = {th["properties"].get("name")}, {peak["properties"].get("name")}')
