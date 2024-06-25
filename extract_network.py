#!/usr/bin/env python
"""Extract a network of notable nodes and paths between them.

A node is notable if:

1. It is a high peak
2. It is the junction of 2+ trails
3. It is the junction of a trail and the road network.

This outputs a list of notable nodes and the paths between them.

Inputs:
- spec.json
- peaks-connected.json
- combined-trails.json
- roads.json

Output: network.geojson
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import sys
from typing import Dict, List, Set, Tuple

import json5
import networkx as nx

from osm import (
    OsmElement,
    OsmNode,
    dedupe_ways,
    find_path,
    node_link,
    way_link,
)
from spec import Spec
from util import haversine, pairkey


@dataclass
class Trail:
    d_km: float
    way: int
    nodes: List[int]
    latlons: List[Tuple[float, float]]


def extract_network(
    spec: Spec,
    peak_nodes: List[OsmNode],
    trail_elements: List[OsmElement],
    road_elements: List[OsmElement],
):
    id_to_peak_node = {el['id']: el for el in peak_nodes}

    node_to_trails = defaultdict(list)
    trail_ways_dupes = [el for el in trail_elements if el['type'] == 'way']
    trail_ways = [*dedupe_ways(trail_ways_dupes)]
    trail_nodes = {
        el['id']: el
        for el in trail_elements
        if el['type'] == 'node'
        # TODO: this filter could probably be applied in the trails.txt query instead.
        and spec.is_in_bbox(el['lon'], el['lat'])
    }
    trail_ways = [
        way for way in trail_ways if all(node in trail_nodes for node in way['nodes'])
    ]
    for el in trail_ways:
        for node in el['nodes']:
            node_to_trails[node].append(el['id'])
    id_to_trail_way = {way['id']: way for way in trail_ways}

    node_to_roads = defaultdict(list)
    road_ways = [el for el in road_elements if el['type'] == 'way']
    if spec.roads_that_are_trails:
        filtered_road_ways = [
            el
            for el in road_ways
            if el['tags'].get('name') not in spec.roads_that_are_trails
        ]
        # There are three hits for "Lake Road"
        assert len(road_ways) - len(filtered_road_ways) >= len(
            spec.roads_that_are_trails
        )
        road_ways = filtered_road_ways
    for el in road_ways:
        for node in el['nodes']:
            node_to_roads[node].append(el['id'])

    # 1. High peaks
    notable_nodes: Dict[int, OsmElement] = {node['id']: node for node in peak_nodes}
    trailhead_nodes: Dict[int, OsmElement] = {}
    assert len(notable_nodes) == spec.num_peaks

    # 2. Junction of 2+ trails
    for node_id, trails in node_to_trails.items():
        node = trail_nodes[node_id]
        if len(trails) >= 2:
            if node_id not in notable_nodes:
                notable_nodes[node_id] = node

        if node_id in node_to_roads:
            trailhead_nodes[node_id] = node

    # 3. Nodes that appear twice in a way (i.e. a loop / lollipop)
    for el in trail_ways:
        node_counts = Counter(el['nodes'])
        for node_id, count in node_counts.items():
            if count >= 2:
                sys.stderr.write(
                    f'{node_link(node_id)} appears 2+ times in {way_link(el["id"])}\n'
                )
                notable_nodes[node_id] = trail_nodes[node_id]

    sys.stderr.write(f'Notable nodes: {len(notable_nodes)}\n')
    sys.stderr.write(f'Trailhead nodes: {len(trailhead_nodes)}\n')

    # Notable nodes: 15406
    # Trailhead nodes: 2077

    # A path can be relevant because it connects a peak/trail, trail/trail or trail/road
    # but not because it connects two roads.
    # (node, node) -> way[]; nodes are sorted
    connections: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for way in trail_ways:
        id = way['id']
        nodes = [
            node
            for node in way['nodes']
            if node in notable_nodes or node in trailhead_nodes
        ]
        if not nodes:
            continue

        for a, b in zip(nodes[:-1], nodes[1:]):
            # At least one node must be notable; they can't both be trailheads.
            if a in notable_nodes or b in notable_nodes:
                key = pairkey(a, b)
                connections[key].append(id)

    sys.stderr.write(f'Connections: {len(connections)}\n')
    for (a, b), ways in connections.items():
        if len(ways) > 1:
            sys.stderr.write(f'Many paths from {a} -> {b}: {ways}\n')

    # Run BFS starting from the high peaks to find the relevant trail network.
    # This should prune out most nodes and paths.
    g = nx.Graph(connections.keys())
    sys.stderr.write(f'nodes: {g.number_of_nodes()}, edges: {g.number_of_edges()}\n')

    peaks_component: Set[int] = set()  # set of nodes connected to high peaks
    for node in peak_nodes:
        id = node['id']
        if id in peaks_component:
            continue
        if id not in g:
            name = node['tags']['name']
            sys.stderr.write(f'Node {id} / {name} is not connected\n')
            continue
        peaks_component.update(nx.node_connected_component(g, id))

    sys.stderr.write(f'Nodes connected to a high peak: {len(peaks_component)}\n')
    peak_g: nx.Graph = g.subgraph(peaks_component).copy()
    sys.stderr.write(
        f'nodes: {peak_g.number_of_nodes()}, edges: {peak_g.number_of_edges()}\n'
    )

    # Fill out the edges a bit:
    # - extract the sequence of coordinates
    # - pick the shorter one (where relevant)
    # - record whether it's trail/trail or road/trail
    paths: list[Trail] = []
    for a, b in peak_g.edges():
        key = pairkey(a, b)
        way_ids = connections[key]
        for way_id in way_ids:
            # Find the subsequence of nodes and calculate a distance
            way = id_to_trail_way[way_id]
            nodes = find_path(way, a, b)
            assert nodes, f'{way}: [{a}, {b}]'
            latlons = []
            for node_id in nodes:
                n = trail_nodes[node_id]
                latlons.append((n['lon'], n['lat']))
            d_km = sum(
                haversine(alon, alat, blon, blat)
                for (alon, alat), (blon, blat) in zip(latlons[:-1], latlons[1:])
            )
            paths.append(
                Trail(
                    d_km=d_km,
                    way=way_id,
                    nodes=nodes,
                    latlons=latlons,
                )
            )

    features = []
    for node_id in peak_g.nodes():
        peak_node = id_to_peak_node.get(node_id)
        if peak_node:
            features.append(
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': (peak_node['lon'], peak_node['lat']),
                    },
                    'properties': {
                        'id': node_id,
                        'type': 'high-peak',
                        **peak_node['tags'],
                        'marker-color': '#0000ff',
                        'marker-size': 'medium',
                        'degree': peak_g.degree[node_id],
                    },
                }
            )
            continue
        trail_node = trail_nodes[node_id]
        features.append(
            {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': (trail_node['lon'], trail_node['lat']),
                },
                'properties': {
                    'id': node_id,
                    'type': 'trailhead' if node_to_roads.get(node_id) else 'junction',
                    **trail_node.get('tags', {}),
                    'marker-size': 'small',
                    'marker-color': (
                        '#00ff00'
                        if peak_g.degree[node_id] == 1
                        and not node_to_roads.get(node_id)
                        else (
                            '#ff00ff'
                            if peak_g.degree[node_id] == 2
                            and not node_to_roads.get(node_id)
                            else (
                                '#555555'
                                if not node_to_roads.get(node_id)
                                else '#ff0000'
                            )
                        )
                    ),
                    'trail-ways': node_to_trails[node_id],
                    'road-ways': node_to_roads.get(node_id, None),
                    'degree': peak_g.degree[node_id],
                },
            }
        )

    for path in paths:
        a, b = path.nodes[0], path.nodes[-1]
        if not peak_g.has_edge(a, b):
            continue  # must have been pruned
        features.append(
            {
                'type': 'Feature',
                'geometry': {'type': 'LineString', 'coordinates': path.latlons},
                'properties': {
                    'id': path.way,
                    'd_km': path.d_km,
                    **id_to_trail_way[path.way].get('tags', {}),
                    'nodes': path.nodes,
                    'stroke': '#555555',
                    'stroke-width': 2,
                    'stroke-opacity': 1,
                },
            }
        )

    return {'type': 'FeatureCollection', 'features': features}


if __name__ == '__main__':
    spec_file, peaks_file, trails_file, roads_file = sys.argv[1:]
    spec = Spec(json5.load(open(spec_file)))
    peaks, trails, roads = (
        json.load(open(path))['elements']
        for path in (peaks_file, trails_file, roads_file)
    )
    network = extract_network(spec, peaks, trails, roads)
    json.dump(network, sys.stdout)
