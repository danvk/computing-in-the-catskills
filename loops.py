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
import math
from typing import List

import networkx as nx

from graph import cycle_weight, make_complete_graph, read_hiking_graph, scale_graph
from noon_bean import gtsp_to_tsp, tsp_solution_to_gtsp
from ort_wrapper import solve_tsp_with_or_tools
from util import rotate_to_start, splitlist

features = json.load(open('data/network.geojson'))['features']
G: nx.Graph
G, id_to_peak, id_to_trailhead = read_hiking_graph(features)
peak_features = [f for f in features if f['properties'].get('type') == 'high-peak']

# Remove trailhead<->trailhead edges
to_remove = []
for a, b in G.edges():
    if a in id_to_trailhead and b in id_to_trailhead:
        to_remove.append((a, b))
G.remove_edges_from(to_remove)

trailhead_to_peaks = {}

for th_node in G.nodes():
    if G.nodes[th_node]['type'] != 'trailhead':
        continue

    # Get the reachable set of non-trailhead nodes from this trailhead
    node_to_length, node_to_path = nx.single_source_dijkstra(G, th_node)
    reachable_nodes = [
        n
        for n in node_to_length.keys()
        if G.nodes[n]['type'] == 'high-peak'
        # This breaks up the Devil's Path East & West
        and not any(G.nodes[k]['type'] == 'trailhead' for k in node_to_path[n][1:-1])
    ]

    if not reachable_nodes:
        print(f'Filtered out trailhead {th_node}')
        continue

    trailhead_to_peaks[th_node] = reachable_nodes

for trailhead, peaks in sorted(trailhead_to_peaks.items(), key=lambda x: len(x[1])):
    print(trailhead, len(peaks), peaks)

print(len(trailhead_to_peaks), 'trailheads')
# 93 trailheads
#  1: 16
#  2:  6
#  4: 42
#  9:  7
# 10: 22

# The 9s are the ones you'd expect
# The 10 is Spruceton + Rusk + Hunter/SW Hunter + Devil's Path
#  these probably mostly don't make sense

# Find all loops starting and ending at the same trailhead and going over at least one high peak.

# total = 0
# n = 9
# for i in range(1, n + 1):
#     total += math.comb(n, i) * math.factorial(i)

#  986409 sequences per 9-peak trailhead
# 9864100 sequences per 10-peak trailhead
# print(f'{total} sequences per {n}-peak trailhead')
