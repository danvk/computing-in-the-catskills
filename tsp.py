#!/usr/bin/env python
"""Run a Traveling Salesman algorithm (TSP) to find the shortest hiking distance."""

import json
import sys
from typing import List

from graph import (
    cycle_weight,
    get_lot_index,
    get_peak_index,
    make_complete_graph,
    read_hiking_graph,
    scale_graph,
)
from ort_wrapper import solve_tsp_with_or_tools
from util import splitlist


def log(*args):
    print(*args, file=sys.stderr)


def run_tsp(features: list):
    G = read_hiking_graph(features)
    id_to_peak = get_peak_index(features)
    id_to_lot = get_lot_index(features)
    peak_features = [*id_to_peak.values()]

    log(f'Input graph: {G.number_of_nodes()} nodes / {G.number_of_edges()} edges')
    log(f'  Peaks: {len(id_to_peak)}')
    log(f'  Parking Lots: {len(id_to_lot)}')

    assert not G.has_node(0)

    # Add an artificial, zero-weight connection between all trailheads to simulate driving.
    nodes = [*G.nodes()]

    for node_id in nodes:
        if id_to_lot.get(node_id):
            G.add_edge(0, node_id, weight=0)

    """
    log(
        'Slide / Slide Lot path:',
        nx.shortest_path(G, 816358667, 2426171552, weight='weight'),
    )
    log(
        'Slide lot / Panther lot:',
        nx.shortest_path(G, 816358667, 816358666, weight='weight'),
    )
    log(
        'Panther lot / trailhead',
        nx.shortest_path(G, 816358666, 213833958, weight='weight'),
    )
    log(
        'Panther / Panther Lot', nx.shortest_path(G, 816358666, 9147145385, weight='weight')
    )
    log('Slide / Panther path:', nx.shortest_path(G, 2426171552, 9147145385))
    """

    GG = make_complete_graph(G, nodes=[*id_to_peak.keys()])
    log(f'Complete graph: {GG.number_of_nodes()} nodes / {GG.number_of_edges()} edges')

    # peak_nodes: List[int] = nx.approximation.traveling_salesman_problem(GG)
    peak_nodes: List[int]
    peak_nodes, cost = solve_tsp_with_or_tools(
        scale_graph(GG, 100), time_limit_secs=600
    )

    # This could yield a better result but does not:
    # init_nodes: List[int] = nx.approximation.traveling_salesman_problem(GG)
    # peak_nodes: List[int] = nx.approximation.simulated_annealing_tsp(GG, init_nodes)

    log(peak_nodes)
    for i, node in enumerate(peak_nodes):
        name = id_to_peak[node]['properties']['name']
        log(f'  {i+1}: {name} ({node})')
    d_km = cycle_weight(GG, peak_nodes)
    d_mi = d_km * 0.621371
    log(f'Total distance: {d_km:.2f} km = {d_mi:.2f} mi')

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

    log(nodes)

    chunks = splitlist(nodes, 0)
    for i, chunk in enumerate(chunks):
        log(f'  {i}: {chunk}')

    tsp_fs = [*peak_features]
    for f in tsp_fs:
        f['properties']['marker-size'] = 'small'

    # TODO: add in elevation
    total_d_km = 0
    for node_seq in chunks:
        tsp_fs.append(id_to_lot[node_seq[0]])
        tsp_fs.append(id_to_lot[node_seq[-1]])
        d_km = sum(G.edges[a, b]['weight'] for a, b in zip(node_seq[:-1], node_seq[1:]))
        total_d_km += d_km
        tsp_fs.append(
            {
                'type': 'Feature',
                'properties': {
                    'nodes': node_seq,
                    'd_km': round(d_km, 2),
                    'd_mi': round(d_km * 0.621371, 2),
                    'peaks': [
                        id_to_peak[node]['properties']['name']
                        for node in node_seq
                        if node in id_to_peak
                    ],
                },
                'geometry': {
                    'type': 'MultiLineString',
                    'coordinates': [
                        G.edges[a, b]['feature']['geometry']['coordinates']
                        for a, b in zip(node_seq[:-1], node_seq[1:])
                    ],
                },
            }
        )

    log(f'Total hiking distance: {total_d_km:.1f} km')
    return tsp_fs


if __name__ == '__main__':
    (network_parking_file,) = sys.argv[1:]
    features = json.load(open(network_parking_file))['features']
    tsp_fs = run_tsp(features)

    json.dump({'type': 'FeatureCollection', 'features': tsp_fs}, sys.stdout)
