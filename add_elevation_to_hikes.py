#!/usr/bin/env python
"""Given a height-annotated netowrk GeoJSON + hikes.json file, add ele gain to hikes."""

import json
import sys
import networkx as nx
from tqdm import tqdm

from graph import read_hiking_graph


def add_ele_to_hikes(
    hikes: list[tuple[float, list[int]]], geojson
) -> list[tuple[float, float, list[int]]]:
    features = geojson['features']
    G = read_hiking_graph(features)
    id_to_feature = {
        f['properties']['id']: f for f in features if 'id' in f['properties']
    }

    # (a, b) -> elevation gain
    cache: dict[tuple[int, int], float] = {}

    out = []
    for d_km, seq in tqdm(hikes):
        ele_gain = 0.0
        for a, b in zip(seq[:-1], seq[1:]):
            up_cache = cache.get((a, b))
            if up_cache is not None:
                ele_gain += up_cache
                continue
            path = nx.shortest_path(G, a, b, weight='weight')
            path_up = 0.0
            path_down = 0.0
            for node_a, node_b in zip(path[:-1], path[1:]):
                f = G.edges[node_a, node_b]['feature']
                p = f['properties']
                up, down = p['ele_gain'], p['ele_loss']
                pt_a = id_to_feature[node_a]['geometry']['coordinates']
                pt_b = id_to_feature[node_b]['geometry']['coordinates']
                start = f['geometry']['coordinates'][0]
                if pt_a != start:
                    assert pt_b == start
                    up, down = down, up
                path_up += up
                path_down += down

            cache[(a, b)] = path_up
            cache[(b, a)] = path_down
            ele_gain += path_up
        out.append((round(d_km, 3), int(ele_gain), seq))
    return out


if __name__ == '__main__':
    geojson_file, hikes_file = sys.argv[1:]
    geojson = json.load(open(geojson_file))
    hikes = json.load(open(hikes_file))

    hikes_with_ele = add_ele_to_hikes(hikes, geojson)
    json.dump(hikes_with_ele, sys.stdout, separators=(',', ':'))
