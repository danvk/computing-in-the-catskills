"""Analyze trailhead/parking lot proximity"""

import json

from tqdm import tqdm
import networkx as nx

from graph import read_hiking_graph
from osm import OsmElement, closest_point_on_trail, distance, element_centroid, element_link, node_link, way_length
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

road_els: list[OsmElement] = json.load(open('data/roads.json'))['elements']
road_ways = [el for el in road_els if el['type'] == 'way']
id_to_road_node = {el['id']: el for el in road_els if el['type'] == 'node'}

# Forcibly add the closest nodes to each parking lot to the road graph,
# even if they're in the middle of a way.
nodes_to_add = set()
for el in tqdm(lots):
    lot_loc = element_centroid(el, lot_nodes)
    d, node = closest_point_on_trail(lot_loc, road_ways, id_to_road_node)
    nodes_to_add.add(node['id'])

road_graph = nx.Graph()
for way in road_ways:
    way_id=way['id']
    nodes = way['nodes']
    # TODO: add distances
    road_graph.add_edge(nodes[0], nodes[-1], way_id=way_id, weight=way_length(nodes, id_to_road_node))
    for i, node in enumerate(nodes[1:-1], start=1):
        if node in nodes_to_add:
            road_graph.add_edge(nodes[0], node, way_id=way_id, weight=way_length(nodes[:i+1], id_to_road_node))
            road_graph.add_edge(node, nodes[-1], way_id=way_id, weight=way_length(nodes[i:], id_to_road_node))

# Road network: 45529 nodes / 26514 edges
# Road network: 45739 nodes / 27004 edges
print(f'Road network: {road_graph.number_of_nodes()} nodes / {road_graph.number_of_edges()} edges')

# How many trailheads have a nearby parking lot?
num_matched, num_unmatched = 0, 0
matched_lots = set()
for trailhead_id in trailheads:
    th = id_to_trailhead[trailhead_id]
    th_lonlat = th['geometry']['coordinates']
    all_lots = [(distance(th_lonlat, lot, lot_nodes), lot) for lot in lots]
    all_lots.sort(key=lambda x: x[0])
    nearby_lots = [(d, lot) for (d, lot) in all_lots if d < 400]
    th_txt = node_link(trailhead_id, th['properties'].get('name'))
    if nearby_lots:
        for _, lot in nearby_lots:
            matched_lots.add(lot['id'])
        print(th_txt)
        for d, lot in nearby_lots:
            print('  ' + element_link(lot) + f' {d:.0f}m')
        num_matched += 1

        lot = nearby_lots[0][1]
        lot_loc = element_centroid(el, lot_nodes)
        d, node = closest_point_on_trail(lot_loc, road_ways, id_to_road_node)
        print(f'  closest road node to lot: {element_link(node)} @ {d:.0f}m')
        print(f'  in graph?', road_graph.has_node(node['id']))
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
print('')

"""
num_matched, num_unmatched = 0, 0
for el in lots:
    if el['type'] == 'node':
        lot_loc = (el['lon'], el['lat'])
    elif el['type'] == 'way':
        node = lot_nodes[el['nodes'][0]]
        lot_loc = (node['lon'], node['lat'])
    d, node = closest_point_on_trail(lot_loc, trail_ways, id_to_trail_node)
    if d < 250:
        num_matched += 1
        if el['id'] not in matched_lots:
            print(f'Unmatched lot {element_link(el)} is {d:.0f}m from trail {element_link(node)}')
    else:
        num_unmatched += 1

# 245 lots matched a trail, 70 did not.
print(f'{num_matched} lots matched a trail, {num_unmatched} did not.')
"""

# For each matched trailhead:
# - if the parking lot is <20m away, add the lot and a link to the trailhead.
# - if the parking lot is <20m away from a node on a trail in network.geojson:
#   - add a link to that node
#   - this might require splitting some paths to promote that node into a junction.
#     (or am I generating network.geojson from OsmElements here?)
# - otherwise:
#   - route from the closest parking lot (as the crow flies) to the trailhead on the road network
#   - repeat while this distance is > the as-the-crow-flies distance to the next closest lot
#   - if this is <1km? then add the lot + route to trailhead to the network.

