"""Use a weighted set cover algorithm to find a minimal set of hiking loops."""
import json

import numpy as np
import networkx as nx
from SetCoverPy import setcover

from graph import get_lot_index, get_peak_index, read_hiking_graph


def find_optimal_hikes_subset_cover(
    features: list, hikes: list, peak_osm_ids: list[int] | None = None
):
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
        cost, loop = hike[:2]
        costs[j] = cost
        for peak in loop[1:-1]:
            if peak in peak_id_to_idx:
                i = peak_id_to_idx[peak]
                covers[i, j] = True

    median_cost = np.median(costs)
    costs = costs / median_cost

    solver = setcover.SetCover(covers, costs)
    solver.SolveSCP()
    # total_cost = solver.total_cost * median_cost
    chosen_hikes = []
    for j, hike in enumerate(hikes):
        if solver.s[j]:
            chosen_hikes.append(hike)

    total_d_km = 0
    tsp_fs = [f for f in peak_features if f['properties']['id'] in peak_id_to_idx]
    for f in tsp_fs:
        f['properties']['marker-size'] = 'small'
    for hike in chosen_hikes:
        d_km, loop = hike[:2]
        cost = None
        if len(hike) > 2:
            cost, loop, d_km = hike
        total_d_km += d_km
        tsp_fs.append(id_to_lot[loop[0]])
        if loop[0] != loop[-1]:
            tsp_fs.append(id_to_lot[loop[-1]])
        coordinates = []
        for a, b in zip(loop[:-1], loop[1:]):
            path = nx.shortest_path(G, a, b, weight='weight')
            coordinates += [
                G.edges[node_a, node_b]['feature']['geometry']['coordinates']
                for node_a, node_b in zip(path[:-1], path[1:])
            ]
        tsp_fs.append(
            {
                'type': 'Feature',
                'properties': {
                    'nodes': loop,
                    'd_km': round(d_km, 2),
                    'd_mi': round(d_km * 0.621371, 2),
                    **({'cost': cost} if cost is not None else {}),
                    'peaks': [
                        id_to_peak[node]['properties']['name'] for node in loop[1:-1]
                    ],
                },
                'geometry': {'type': 'MultiLineString', 'coordinates': coordinates},
            }
        )

    return total_d_km, chosen_hikes, {'type': 'FeatureCollection', 'features': tsp_fs}


if __name__ == '__main__':
    features = json.load(open('data/network+parking.geojson'))['features']
    all_hikes: list[tuple[float, list[int]]] = json.load(open('data/hikes.json'))

    print(f'Unrestricted hikes: {len(all_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, all_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/unrestricted.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    loop_hikes = [(d, nodes) for d, nodes in all_hikes if nodes[0] == nodes[-1]]
    print(f'Loop hikes: {len(loop_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, loop_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/loops-only.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    day_hikes = [(d, nodes) for d, nodes in all_hikes if d < 21]  # 21km = ~13 miles
    print(f'Day hikes: {len(day_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, day_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/day-hikes-only.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    day_loop_hikes = [
        (d, nodes) for d, nodes in loop_hikes if d < 21
    ]  # 21km = ~13 miles
    print(f'Day loop hikes: {len(day_loop_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, day_loop_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/day-loop-hikes-only.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    penalized_hikes = [
        (d + (0 if nodes[0] == nodes[-1] else 3.5), nodes, d) for d, nodes in all_hikes
    ]
    print(f'Preferred loop hikes: {len(day_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, penalized_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/prefer-loop-hikes.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    penalized_day_hikes = [
        (cost, nodes, d_km) for cost, nodes, d_km in penalized_hikes if d_km < 21
    ]
    print(f'Preferred loop day hikes: {len(penalized_day_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, penalized_day_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/day-prefer-loop-hikes.geojson', 'w') as out:
        json.dump(fc, out)
