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

trail_g = nx.Graph()

for th_node in G.nodes():
    if G.nodes[th_node]['type'] != 'trailhead':
        continue

    # Get the reachable set of non-trailhead nodes from this trailhead
    node_to_length = nx.single_source_dijkstra_path_length(G, th_node)
    reachable_nodes = [
        n
        for n in node_to_length.keys()
        if G.nodes[n]['type'] != 'trailhead'
    ]

    if not reachable_nodes:
        print(f'Filtered out trailhead {th_node}')
        continue

    trail_g.add_node(th_node, type='trailhead')

    # Add a copy of this subgraph tagged with the trailhead.
    for node in reachable_nodes:
        tagged_node = (th_node, node)
        trail_g.add_node(tagged_node, type=G.nodes[node]['type'])
        for neighbor in G[node]:
            if G.nodes[neighbor].get('type') == 'trailhead':
                if neighbor != th_node:
                    # If you walk to another trailhead, it's just another node.
                    neighbor_node = (th_node, neighbor)
                else:
                    neighbor_node = neighbor
            else:
                neighbor_node = (th_node, neighbor)
            trail_g.add_edge(tagged_node, neighbor_node, weight=G.edges[node, neighbor]['weight'])

peak_nodes = [
    n for n in trail_g.nodes()
    if isinstance(n, tuple) and G.nodes[n[1]]['type'] == 'high-peak'
]

# 479 trailhead/peak tuples
# Trailhead-tagged graph: 9,699 nodes / 11,171 edges.
print(f'{len(peak_nodes)} trailhead/peak tuples')
print(f'Trailhead-tagged graph: {trail_g.number_of_nodes():,} nodes / {trail_g.number_of_edges():,} edges.')

# for trailhead_id, peak_id in tuples:
#     th = id_to_trailhead[trailhead_id]
#     peak = id_to_peak[peak_id]
#     print(f'  {trailhead_id}, {peak_id} = {th["properties"].get("name")}, {peak["properties"].get("name")}')

# Add artificial zero node to connect trailheads
nodes = [*trail_g.nodes()]
for node_id in nodes:
    if id_to_trailhead.get(node_id):
        trail_g.add_edge(0, node_id, weight=0)

# The issue here is that you can only from Notch Inn Rd to SW Hunter by walking through the SR 214 trailhead
# Missing (212271460, 2882649917) (212379716, 1938215682)
#          SR 214     Plateau      Notch Inn, SW Hunter

# The issue here was that there was a "trailhead" that was only connected to paths via another trailhead.
# print(trail_g[212271460])
# print(trail_g[2884528159])

GG = make_complete_graph(trail_g, nodes=peak_nodes)
# Remove paths from a peak back to itself via a different trailheads.
# These aren't needed for the solution and violate the preconditions for Noon-Bean.
to_delete = []
for n1, n2 in GG.edges():
    (_, peak_a) = n1
    (_, peak_b) = n2
    if peak_a == peak_b:
        to_delete.append((n1, n2))
print(f'Deleting {len(to_delete)} peak->same peak edges.')
GG.remove_edges_from(to_delete)

# Complete graph: 479 nodes / 109917 edges
print(f'Complete graph: {GG.number_of_nodes()} nodes / {GG.number_of_edges()} edges')

# friday_moon_haw = (7609349952, 9953707705)  # Friday via Moon Haw
# 7609349952 -- Moon Haw Road
# balsam_cap_moon_haw = (7609349952, 9953729846)  # Balsam Cap via Moon Haw

# assert GG.has_edge(friday_moon_haw, balsam_cap_moon_haw)
# print(f'Moon Haw d=', GG.edges[friday_moon_haw, balsam_cap_moon_haw]['weight'])
# print(f'Moon Haw path=', GG.edges[friday_moon_haw, balsam_cap_moon_haw]['path'])

peak_sets = [
    [
        (th, node_id)
        for (th, node_id) in peak_nodes
        if node_id == peak_id
    ]
    for peak_id in sorted(id_to_peak.keys())
]
print(peak_sets)

gtsp = gtsp_to_tsp(GG, peak_sets)
max_edge = max(w for _a, _b, w in gtsp.edges.data('weight'))

print(f'Transformed complete graph: {gtsp.number_of_nodes()} nodes / {gtsp.number_of_edges()} edges / max edge={max_edge}')
solution, solution_dist = solve_tsp_with_or_tools(scale_graph(gtsp, 100), 60)
print(solution)
true_soln = tsp_solution_to_gtsp(solution, peak_sets)
print(true_soln)
d_km = cycle_weight(GG, true_soln)
print(f'Total distance: {d_km:.2f} km')

nodes = []
for a, b in zip(true_soln[:-1], true_soln[1:]):
    if not GG.has_edge(a, b):
        print('Going to fail on:', a, b)
    path = GG.edges[a, b]['path']
    if path[0] != a:
        path = [*path[::-1]]
    print(a, b, path)
    assert path[0] == a
    assert path[-1] == b
    nodes += path[:-1]

nodes = rotate_to_start(nodes, 0)
print(nodes)

# this is a hack that doesn't make sense
filtered_nodes = [nodes[0]]
for i in range(1, len(nodes)):
    prev = nodes[i - 1]
    n = nodes[i]
    next_node = nodes[i + 1] if i < len(nodes) - 1 else None

    if isinstance(n, tuple):
        filtered_nodes.append(n)
    elif isinstance(prev, tuple) and isinstance(next_node, tuple) and prev[0] == n and n == next_node[0]:
        pass  # never makes sense to needlessly go back to the trailhead
    else:
        filtered_nodes.append(n)
nodes = filtered_nodes

def second_or_scalar(x):
    if isinstance(x, tuple):
        return x[1]
    return x


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
    for a, b in zip(node_seq[:-1], node_seq[1:]):
        if not G.has_edge(second_or_scalar(a), second_or_scalar(b)):
            raise KeyError(a, b)
    d_km = sum(
        G.edges[second_or_scalar(a), second_or_scalar(b)]['weight']
        for a, b in zip(node_seq[:-1], node_seq[1:])
    )
    total_d_km += d_km
    tsp_fs.append({
        'type': 'Feature',
        'properties': {
            'nodes': node_seq,
            'd_km': round(d_km, 2),
            'd_mi': round(d_km * 0.621371, 2),
            'peaks': [
                id_to_peak[node]['properties']['name']
                for node in node_seq
                if node in id_to_peak
            ]
        },
        'geometry': {
            'type': 'MultiLineString',
            'coordinates': [
                G.edges[second_or_scalar(a), second_or_scalar(b)]['feature']['geometry']['coordinates']
                for a, b in zip(node_seq[:-1], node_seq[1:])
            ]
        }
    })


with open('data/loop-tsp.geojson', 'w') as out:
    json.dump({'type': 'FeatureCollection', 'features': tsp_fs}, out)

print(f'Total hiking distance: {total_d_km:.1f} km')
