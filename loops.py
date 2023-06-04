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
# print(peak_sets)

gtsp = gtsp_to_tsp(GG, peak_sets)
max_edge = max(w for _a, _b, w in gtsp.edges.data('weight'))

print(f'Transformed complete graph: {gtsp.number_of_nodes()} nodes / {gtsp.number_of_edges()} edges / max edge={max_edge}')

solution, solution_dist = solve_tsp_with_or_tools(scale_graph(gtsp, 100), time_limit_secs=600)
print(solution)
true_soln = tsp_solution_to_gtsp(solution, peak_sets)

print('True Solution:')
# true_soln = [(7988852640, 10033501291), (212271460, 10010091368), (7894979775, 2897919022), (213757228, 9147145385), (10010074986, 357563196), (212334242, 2955311547), (7609349952, 2884119672), (7609349952, 2426171552), (212320092, 2473476747), (212320092, 2473476912), (212320092, 2473476927), (6289621586, 7292479776), (6289621586, 2398015279), (212397952, 2882649917), (212334582, 357574030), (4168457690, 9953707705), (10005350826, 2426236522), (212329873, 10010051278), (212329873, 212348771), (212357867, 9785950126), (2884119781, 2884119551), (213609657, 2845338212), (213609657, 357557378), (213609657, 357548762), (213609657, 357559622), (7609349952, 9953729846), (7609349952, -538), (7609349952, -1136), (7988852640, 1938215682), (7988852640, 1938201532), (7988852640, 2882649730), (7988852640, 7982977638), (212334242, 7978185605), (2936274595, 2884119551), (212334242, 7982977638)]
print(true_soln)
d_km = cycle_weight(GG, true_soln)
print(f'Total distance: {d_km:.2f} km')
peak_set_counts = {
    peak_set[0][1]: sum(
        1
        for n in true_soln
        for peak in peak_set
        if n == peak
    )
    for peak_set in peak_sets
}
print('Trips to each peak (should be 1 for each):')
print(peak_set_counts)
all_ok = True
for peak_id, count in peak_set_counts.items():
    if count != 1:
        print(f'Incorrect number of visits to {peak_id}: {count} (want 1)')
        all_ok = False
assert all_ok

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

def second_or_scalar(x):
    if isinstance(x, tuple):
        return x[1]
    return x

# This is Cortina Ln out and back to Kaaterskill High Peak. Perfect!
# [
#   212357867,
#   (212357867, 2908399218),
#   (212357867, 1278701329),
#   (212357867, 1278702498),
#   (212357867, 9785950126),
#   (212357867, 1278702498),
#   (212357867, 1278701329),
#   (212357867, 2908399218),
#   212357867
# ]

chunks = splitlist(nodes, 0)
for i, chunk in enumerate(chunks):
    print(f'  {i}: {chunk}')

tsp_fs = [*peak_features]
for f in tsp_fs:
    f['properties']['marker-size'] = 'small'

total_d_km = 0
for node_seq in chunks:
    assert isinstance(node_seq[0], int)
    assert node_seq[0] == node_seq[-1]
    for node in node_seq[1:-1]:
        assert isinstance(node, tuple)
        assert node[0] == node_seq[0]

    node_seq = [second_or_scalar(n) for n in node_seq]

    tsp_fs.append(id_to_trailhead[node_seq[0]])
    tsp_fs.append(id_to_trailhead[node_seq[-1]])
    for a, b in zip(node_seq[:-1], node_seq[1:]):
        if not G.has_edge(a, b):
            raise KeyError(a, b)
    d_km = sum(
        G.edges[a, b]['weight']
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
                G.edges[a, b]['feature']['geometry']['coordinates']
                for a, b in zip(node_seq[:-1], node_seq[1:])
            ]
        }
    })


with open('data/loop-tsp.geojson', 'w') as out:
    json.dump({'type': 'FeatureCollection', 'features': tsp_fs}, out)

print(f'Total hiking distance: {total_d_km:.1f} km')

"""
[
    212334242,  # spruceton rd / devil's path
    (212334242, 2953604183),
    (212334242, 2955311547),
    (212334242, 2955311754),
    (212334242, 10091139169),
    (212334242, 10091139170),
    (212334242, 1938245944),
    (212334242, 1938215691),
    (212334242, 212344919),
    (212334242, 212344950),
    (212334242, 7644271840),
    (212334242, 7644271839),
    (212334242, 7988852669),
    (212334242, 212271460),
    (212334242, 2895935508),
    (212334242, 7644223407),
    (212334242, 2895889197),
    (212334242, 2882649917),
    (212334242, 2882649793),
    (212334242, 2882649784),
    (212334242, 2882649729),
    (212334242, 2882649730),
    (212334242, 2463484008), # devil's path pecoy notch (bt Sugarloaf and Twin)
    # this jump makes no sense and isn't really valid?
    (7988852640, 10033501291), # SR 214 / Rusk Mountain
    (7988852640, 10033501292),
    (7988852640, 10033564844),
    (7988852640, 1938157148),
    (7988852640, 1938157056),
    (7988852640, 1938156968),
    (7988852640, 5857246059),
    (7988852640, 1938201532),
    (7988852640, 1938201509),
    (7988852640, 212344919),
    (7988852640, 212344950),
    (7988852640, 7644271840),
    (7988852640, 7644271839),
    (7988852640, 7988852669),
    7988852640
]
"""