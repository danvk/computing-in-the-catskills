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

solver = setcover.SetCover(covers, costs)
solution, time_used = solver.SolveSCP()
print('d_km: ', solver.total_cost)
for j, (d, loop) in enumerate(all_loops):
    if solver.s[j]:
        print(d, loop)
