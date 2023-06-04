import json

import numpy as np
import networkx as nx
from SetCoverPy import setcover

from graph import read_hiking_graph

loops = json.load(open('data/loops.json'))

all_loops = [
    (d, [loop['trailhead'], *peaks, loop['trailhead']])
    for loop in loops
    for (d, peaks) in loop['cycles']
]

num_loops = len(all_loops)

features = json.load(open('data/network.geojson'))['features']
G: nx.Graph
G, id_to_peak, id_to_trailhead = read_hiking_graph(features)
peak_features = [f for f in features if f['properties'].get('type') == 'high-peak']

num_peaks = len(peak_features)
peak_id_to_idx = {f['properties']['id']: i for i, f in enumerate(peak_features)}

covers = np.zeros(shape=(num_peaks, num_loops), dtype=bool)
costs = np.zeros(shape=(num_loops,), dtype=float)
for j, (d, loop) in enumerate(all_loops):
    costs[j] = d
    for peak in loop[1:-1]:
        i = peak_id_to_idx[peak]
        covers[i, j] = True

median_cost = np.median(costs)
costs = costs / median_cost

solver = setcover.SetCover(covers, costs)
solution, time_used = solver.SolveSCP()
print('d_km: ', solver.total_cost * median_cost)
chosen_loops = []
for j, (d, loop) in enumerate(all_loops):
    if solver.s[j]:
        chosen_loops.append((d, loop))

tsp_fs = [*peak_features]
for f in tsp_fs:
    f['properties']['marker-size'] = 'small'
for d_km, loop in chosen_loops:
    tsp_fs.append(id_to_trailhead[loop[0]])
    # tsp_fs.append(id_to_trailhead[loop[-1]])
    coordinates = []
    for a, b in zip(loop[:-1], loop[1:]):
        path = nx.shortest_path(G, a, b, weight='weight')
        coordinates.append([
            coord
            for node_a, node_b in zip(path[:-1], path[1:])
            for coord in G.edges[node_a, node_b]['feature']['geometry']['coordinates']
        ])
    tsp_fs.append({
        'type': 'Feature',
        'properties': {
            'nodes': loop,
            'd_km': round(d_km, 2),
            'd_mi': round(d_km * 0.621371, 2),
            'peaks': [
                id_to_peak[node]['properties']['name']
                for node in loop[1:-1]
            ]
        },
        'geometry': {
            'type': 'MultiLineString',
            'coordinates': coordinates
        }
    })

with open('data/loop-tsp.geojson', 'w') as out:
    json.dump({'type': 'FeatureCollection', 'features': tsp_fs}, out)
