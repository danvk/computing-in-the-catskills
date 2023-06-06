"""Analyze trailhead/parking lot proximity"""

import json

import networkx as nx

from graph import read_hiking_graph
from osm import OsmElement, closest_point_on_trail, distance, element_link, node_link
from util import haversine

features = json.load(open('data/network.geojson'))['features']
raw_trailheads = [f for f in features if f['properties'].get('type') == 'trailhead']

raw_trails = json.load(open('data/combined-trails.json'))['elements']
trail_ways = [el for el in raw_trails if el['type'] == 'way']
id_to_trail_node = {el['id']: el for el in raw_trails if el['type'] == 'node'}

# Found 120 trailheads
print(f'Found {len(raw_trailheads)} trailheads in network.geojson')

G: nx.Graph
G, id_to_peak, id_to_trailhead = read_hiking_graph(features)

# We only want trailheads where you can hike from a trailhead to a high peak
# without walking over another trailhead.
trailheads = []
for th_node in G.nodes():
    if G.nodes[th_node]['type'] != 'trailhead':
        continue

    node_to_length, node_to_path = nx.single_source_dijkstra(G, th_node)
    reachable_nodes = [
        n
        for n in node_to_length.keys()
        if G.nodes[n]['type'] == 'high-peak'
        and not any(G.nodes[k]['type'] == 'trailhead' for k in node_to_path[n][1:-1])
    ]

    if reachable_nodes:
        trailheads.append(th_node)

# After filtering: 76
print(f'After filtering: {len(trailheads)}')

# Parking lots can be either nodes or ways
parking_elements: list[OsmElement] = json.load(open('data/parking.json'))['elements']
lots = [
    el
    for el in parking_elements
    if el.get('tags', {}).get('amenity') == 'parking'  # exclude nodes that are part of parking ways
]
lot_nodes = {el['id']: el for el in parking_elements if el['type'] == 'node'}

# Found 315 parking lots.
print(f'Found {len(lots)} parking lots.')

# How many trailheads have a nearby parking lot?
num_matched, num_unmatched = 0, 0
for trailhead_id in trailheads:
    th = id_to_trailhead[trailhead_id]
    th_lonlat = th['geometry']['coordinates']
    all_lots = [(distance(th_lonlat, lot, lot_nodes), lot) for lot in lots]
    all_lots.sort(key=lambda x: x[0])
    nearby_lots = [(d, lot) for (d, lot) in all_lots if d < 250]
    th_txt = node_link(trailhead_id, th['properties'].get('name'))
    if nearby_lots:
        print(th_txt)
        for d, lot in nearby_lots:
            print('  ' + element_link(lot) + f' {d:.0f}m')
        num_matched += 1
    else:
        print(f'{th_txt}: no nearby lots')
        d, el = all_lots[0]
        print(f'  Closest is {d:.0f}m ' + element_link(el))
        num_unmatched += 1
        if el['type'] == 'node':
            lot_loc = (el['lon'], el['lat'])
        elif el['type'] == 'way':
            node = lot_nodes[el['nodes'][0]]
            lot_loc = (node['lon'], node['lat'])
        d, node = closest_point_on_trail(lot_loc, trail_ways, id_to_trail_node)
        print(f'  closest trail point to that lot is {node_link(node["id"])} @ {d:.0f}m')

print(f'{num_matched} trailheads matched, {num_unmatched} unmatched.')
