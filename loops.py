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

# Complete graph: 624 nodes / 186952 edges
print(f'Complete graph: {GG.number_of_nodes()} nodes / {GG.number_of_edges()} edges')

peak_sets = [
    [
        (th, node_id)
        for (th, node_id) in peak_nodes
        if node_id == peak_id
    ]
    for peak_id in sorted(id_to_peak.keys())
]
print(peak_sets)

"""
gtsp = gtsp_to_tsp(GG, peak_sets)
max_edge = max(w for _a, _b, w in gtsp.edges.data('weight'))

print(f'Transformed complete graph: {gtsp.number_of_nodes()} nodes / {gtsp.number_of_edges()} edges / max edge={max_edge}')
solution, solution_dist = solve_tsp_with_or_tools(scale_graph(gtsp, 100), 60)
print(solution)
true_soln = tsp_solution_to_gtsp(solution, peak_sets)
print(true_soln)
d_km = cycle_weight(GG, true_soln)
print(f'Total distance: {d_km:.2f} km')
"""
true_soln = [
    (213669242, 2897919022),
    (1272964775, 7978185605),
    (7609349952, 9953707705),
    (7609349952, 9953729846),
    (7988852640, 1938215682),
    (7988852640, 2882649917),
    (7988852640, 1938201532),
    (7988852640, 2882649730),
    (7988852640, 2955311547),
    (212334582, 357574030),
    (213756344, 7292479776),
    (1453293499, 2398015279),
    (212357867, 9785950126),
    (213838962, 357557378),
    (116518006, 10010051278),
    (213839051, 357548762),
    (2884566694, 357559622),
    (7609349952, 2884119551),
    (7609349952, -538),
    (7609349952, 2884119672),
    (212320092, 2473476747),
    (7988852640, 10033501291),
    (1329053809, 2473476912),
    (1329053809, 2473476927),
    (7944990851, 2426236522),
    (7685464670, 2845338212),
    (10010074986, 357563196),
    (116518006, 212348771),
    (9147145531, 9147145385),
    (7609349952, 2426171552),
    (7609349952, -1136),
    (212334582, 10010091368),
    (212296078, 7982977638)
]

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
