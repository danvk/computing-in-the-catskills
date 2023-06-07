#!/usr/bin/env python
"""Find all reasonable loop/out-and-back hikes."""

import itertools
import json
import math
from typing import List

import networkx as nx

from graph import cycle_weight, make_complete_graph, read_hiking_graph
from osm import node_link

features = json.load(open('data/network+parking.geojson'))['features']
G: nx.Graph
G, id_to_peak, id_to_trailhead, id_to_lot = read_hiking_graph(features)
peak_features = [f for f in features if f['properties'].get('type') == 'high-peak']

# This walk connects the Devil's Path to the Panther/Slide area, which is not desirable.
G.remove_edge(385488241, 385488236)
G.remove_edge(385488238, 385488236)

# Now we have:
# 8 10s
# 24 12s

total = 0
n = 11
for i in range(1, n + 1):
    total += math.comb(n, i) * math.factorial(i)
print(total)

lot_to_peaks = {}

for lot_node in G.nodes():
    if G.nodes[lot_node]['type'] != 'parking-lot':
        continue

    # Get the reachable set of non-trailhead nodes from this trailhead
    node_to_length, node_to_path = nx.single_source_dijkstra(G, lot_node)
    reachable_nodes = [
        n
        for n in node_to_length.keys()
        if G.nodes[n]['type'] == 'high-peak'
    ]

    if not reachable_nodes:
        print(f'Filtered out lot {lot_node}')
        continue

    lot_to_peaks[lot_node] = reachable_nodes

for lot, peaks in sorted(lot_to_peaks.items(), key=lambda x: len(x[1])):
    print(node_link(lot), len(peaks), peaks)

print(len(lot_to_peaks), 'lots')

# 2955316486 6 [2955311547, 1938215682, 1938201532, 357574030, 10033501291, 10010091368]

def powerset(xs):
    return (combo for r in range(len(xs) + 1) for combo in itertools.combinations(xs, r))


def loops_for_lot(g, lot_node, peaks):
    loops = []
    gp = make_complete_graph(g, peaks + [lot_node])
    for peak_subset in powerset(peaks):
        if not peak_subset:
            continue

        best_d = math.inf
        best_cycle = None
        for cycle in itertools.permutations(peak_subset):
            cycle = [lot_node, *cycle, lot_node]
            d = cycle_weight(gp, cycle)
            if d < best_d:
                best_d = d
                best_cycle = cycle
        all_peaks = {
            node
            for a, b in zip(best_cycle[:-1], best_cycle[1:])
            for node in gp.edges[a, b]['path']
            if g.nodes[node]['type'] == 'high-peak'
        }
        if len(all_peaks) == len(peak_subset):
            # Exclude paths that go over unexpected peaks.
            # A more stringent check would also exclude paths that go within ~100m of unexpected peaks.
            loops.append((best_d, best_cycle[1:-1]))

    return loops

all_cycles = []
for lot, peaks in lot_to_peaks.items():
    all_cycles.append({
        'trailhead': lot,
        'cycles': loops_for_lot(G, lot, peaks)
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

#       986,409 sequences per 9-peak trailhead
#     9,864,100 sequences per 10-peak trailhead
#   108,505,111 sequences per 11-peak trailhead
# 1,302,061,344 sequences per 12-peak trailhead
# print(f'{total} sequences per {n}-peak trailhead')

"""
This is the group of 12:
https://openstreetmap.org/node/1938215682, SW Hunter
https://openstreetmap.org/node/2882649917, Plateau
https://openstreetmap.org/node/1938201532, Hunter
https://openstreetmap.org/node/2882649730, Sugarloaf
https://openstreetmap.org/node/7982977638, Twin
https://openstreetmap.org/node/2955311547, Westkill
https://openstreetmap.org/node/10033501291, Rusk
https://openstreetmap.org/node/7978185605, Indian Head
https://openstreetmap.org/node/357574030, North Dome
https://openstreetmap.org/node/10010091368, Sherrill
https://openstreetmap.org/node/9785950126, Kaaterskill
https://openstreetmap.org/node/357563196, Halcott
"""