"""Use a weighted set cover algorithm to find a minimal set of hiking loops."""

import numpy as np
import networkx as nx
from SetCoverPy import setcover

from graph import get_lot_index, get_peak_index, read_hiking_graph
from util import orient


def find_optimal_hikes_subset_cover(
    features: list, hikes: list, peak_osm_ids: list[int] | None = None, maxiters=20
):
    """hikes is a list of either:

    - (d_km, ele_m, nodes_list)
    - (cost, ele_m, nodes_list, d_km)
    """
    G = read_hiking_graph(features)
    id_to_peak = get_peak_index(features)
    id_to_lot = get_lot_index(features)
    peak_features = [*id_to_peak.values()]
    if not peak_osm_ids:
        peak_osm_ids = [f['properties']['id'] for f in peak_features]
    num_loops = len(hikes)
    num_peaks = len(peak_osm_ids)
    peak_id_to_idx = {osm_id: i for i, osm_id in enumerate(peak_osm_ids)}

    covers = np.zeros(shape=(num_peaks, num_loops), dtype=bool)
    costs = np.zeros(shape=(num_loops,), dtype=float)
    for j, hike in enumerate(hikes):
        cost, _ele, loop = hike[:3]
        costs[j] = cost
        for peak in loop[1:-1]:
            if peak in peak_id_to_idx:
                i = peak_id_to_idx[peak]
                covers[i, j] = True

    median_cost = np.median(costs)
    costs = costs / median_cost

    solver = setcover.SetCover(covers, costs, maxiters=maxiters)
    solver.SolveSCP()
    chosen_hikes = []
    for j, hike in enumerate(hikes):
        if solver.s[j]:
            chosen_hikes.append(hike)

    total_d_km = 0
    tsp_fs = [f for f in peak_features if f['properties']['id'] in peak_id_to_idx]
    id_to_feature = {
        f['properties']['id']: f for f in features if 'id' in f['properties']
    }
    for f in tsp_fs:
        f['properties']['marker-size'] = 'small'
    for i, hike in enumerate(chosen_hikes):
        d_km, ele_m, loop = hike[:3]
        cost = None
        if len(hike) > 3:
            cost, ele_m, loop, d_km = hike
        total_d_km += d_km
        tsp_fs.append(id_to_lot[loop[0]])
        if loop[0] != loop[-1]:
            tsp_fs.append(id_to_lot[loop[-1]])
        coordinates = []
        for a, b in zip(loop[:-1], loop[1:]):
            path = nx.shortest_path(G, a, b, weight='weight')
            coordinates += [
                orient(
                    G.edges[node_a, node_b]['feature']['geometry']['coordinates'],
                    id_to_feature[node_a]['geometry']['coordinates'],
                )
                for node_a, node_b in zip(path[:-1], path[1:])
            ]
        tsp_fs.append(
            {
                'type': 'Feature',
                'properties': {
                    'nodes': loop,
                    'hike_index': i,
                    'd_km': round(d_km, 2),
                    'd_mi': round(d_km * 0.621371, 2),
                    'ele_m': ele_m,
                    'ele_ft': int(ele_m * 3.28084),
                    **({'cost': cost} if cost is not None else {}),
                    'peaks': [
                        id_to_peak[node]['properties']['name'] for node in loop[1:-1]
                    ],
                },
                'geometry': {'type': 'MultiLineString', 'coordinates': coordinates},
            }
        )

    return total_d_km, chosen_hikes, {'type': 'FeatureCollection', 'features': tsp_fs}
