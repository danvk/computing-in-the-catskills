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

import itertools
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

# 2955316486 6 [2955311547, 1938215682, 1938201532, 357574030, 10033501291, 10010091368]

def powerset(xs):
    return (combo for r in range(len(xs) + 1) for combo in itertools.combinations(xs, r))


def loops_for_trailhead(g, th_node, peaks):
    loops = []
    gp = make_complete_graph(g, peaks + [th_node])
    for peak_subset in powerset(peaks):
        if not peak_subset:
            continue

        best_d = math.inf
        best_cycle = None
        for cycle in itertools.permutations(peak_subset):
            cycle = [th_node, *cycle, th_node]
            d = cycle_weight(gp, cycle)
            if d < best_d:
                best_d = d
                best_cycle = cycle
        # TODO: only add loops that don't include extra peaks
        all_peaks = {
            node
            for a, b in zip(best_cycle[:-1], best_cycle[1:])
            for node in gp.edges[a, b]['path']
            if g.nodes[node]['type'] == 'high-peak'
        }
        if len(all_peaks) == len(peak_subset):
            # Exclude paths that go over unexpected peaks.
            # A more stringent check would also allow paths that go within ~100m of unexpected peaks.
            loops.append((best_d, best_cycle[1:-1]))
        # if best_cycle == [7609349952, 2884119551, 7609349952]:
        #     for a, b in zip(best_cycle[:-1], best_cycle[1:]):
        #         print(f'{a} -> {b} {gp.edges[a, b]["weight"]:.2f}')
        #         path = gp.edges[a, b]['path']
        #         if path[0] != a:
        #             path = path[::-1]
        #         for node in path:
        #             print(f'  https://www.openstreetmap.org/node/{node}')
    return loops

all_cycles = []
for trailhead, peaks in trailhead_to_peaks.items():
    all_cycles.append({
        'trailhead': trailhead,
        'cycles': loops_for_trailhead(G, trailhead, peaks)
    })

with open('data/loops.json', 'w') as out:
    json.dump(all_cycles, out)

# 960 total cycles
# print(len(all_cycles), 'total cycles')

# sample = loops_for_trailhead(G, 2955316486, [2955311547, 1938215682, 1938201532, 357574030, 10033501291, 10010091368])
# print(len(sample), sample)
# sample = loops_for_trailhead(G, 7609349952, [9953707705, 9953729846, 2884119551, -538, 2884119672, 2426171552, -1136, 7292479776, 2398015279])
# sample = loops_for_trailhead(G, 212271460, [1938215682, 2882649917, 1938201532, 2882649730, 7982977638, 2955311547, 10033501291, 7978185605, 357574030, 10010091368])
# print(len(sample))
# print(sample[0][1][0])
# for d, cycle in sample:
#     print(f'{d:.2f}km:', '->'.join(id_to_peak[node]['properties']['name'] + f' ({node})' for node in cycle[1:-1]))

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
