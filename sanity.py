#!/usr/bin/env python

import json
from typing import Dict, List, Literal, TypedDict, Union
from collections import defaultdict

from util import haversine


class OsmElementBase(TypedDict):
    id: int
    tags: Dict[str, any]


class OsmNode(OsmElementBase):
    type: Literal['node']
    lat: float
    lon: float


class OsmWay(OsmElementBase):
    type: Literal['way']
    nodes: List[int]


class RelationMember(TypedDict):
    type: Union[Literal['way'], Literal['node'], Literal['relation']]
    ref: int
    role: str


class OsmRelation(OsmElementBase):
    type: Literal['relation']
    members: List[RelationMember]


OsmElement = Union[OsmNode, OsmWay, OsmRelation]


peak_nodes: List[OsmNode] = json.load(open('data/peaks-3500.json'))['elements']
assert len(peak_nodes) == 33

node_id_to_peak = {n['id']: n for n in peak_nodes}


trail_elements: List[OsmElement] = json.load(open('data/trails.json'))['elements']
node_to_trails = defaultdict(list)
trail_ways = [el for el in trail_elements if el['type'] == 'way']
for el in trail_ways:
    for node in el['nodes']:
        node_to_trails[node].append(el['id'])
trail_nodes = {
    el['id']: el
    for el in trail_elements
    if el['type'] == 'node'
}


def closest_point_on_trail(node: OsmNode):
    best_node = None
    best_d = 1000
    lon1 = node['lon']
    lat1 = node['lat']

    for way in trail_ways:
        for node_id in way['nodes']:
            node = trail_nodes[node_id]
            lon2 = node['lon']
            lat2 = node['lat']
            d = haversine(lon1, lat1, lon2, lat2)
            if d < best_d:
                best_d = d
                best_node = node
    return best_d * 1000, best_node

# Vly: lon=-74.448885, lat=42.245836
# The End of the herd path is node 10010051278

# Trails to summits; summits without trails
for peak in peak_nodes:
    name = peak['tags']['name']
    peak_id = peak['id']
    if name == 'Vly Mountain':
        peak['lat'] = 42.245836
        peak['lon'] = -74.448885
    trails = node_to_trails.get(peak_id)
    if trails:
        print(f'{len(trails)} for {name} ({peak_id})')
    else:
        print(f'{name} ({peak_id})')
        pt_m, pt_node = closest_point_on_trail(peak)
        if pt_m < 30:
            print(f'  Closest point: {pt_m} / {pt_node}')
        else:
            print(f'  No nearby trails for {name} ({peak_id}); closest {pt_m} {pt_node}')
