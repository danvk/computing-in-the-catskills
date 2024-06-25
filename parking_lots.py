"""Analyze trailhead/parking lot proximity.

Inputs:
- spec
- network.geojson
- combined-trails.json
- roads.json
- parking.json
- extra-lot-names.json

Output:
- parking-connections.geojson
- network+parking.geojson
"""

from collections import defaultdict
import json
import sys

import json5
from tqdm import tqdm
import networkx as nx

from graph import get_trailhead_index, read_hiking_graph
from osm import OsmElement, closest_point_on_trail, element_centroid, node_link
from spec import Spec
from util import haversine


def attach_parking(
    spec: Spec,
    features: list,
    raw_trails: list[OsmElement],
    parking_elements: list[OsmElement],
    road_els: list[OsmElement],
    extra_names: list[tuple[int, str]],
):
    raw_trailheads = [f for f in features if f['properties'].get('type') == 'trailhead']
    trail_ways = [el for el in raw_trails if el['type'] == 'way']
    id_to_trail_node = {el['id']: el for el in raw_trails if el['type'] == 'node'}

    # Found 120 trailheads
    sys.stderr.write(f'Found {len(raw_trailheads)} trailheads in network.geojson\n')

    G = read_hiking_graph(features)
    id_to_trailhead = get_trailhead_index(features)

    id_to_extra_name = {id: name for id, name in extra_names}

    # We only want trailheads where you can hike from a trailhead to a high peak
    # without walking over another trailhead.
    trailheads: list[int] = []
    for th_node in G.nodes():
        if G.nodes[th_node]['type'] != 'trailhead':
            continue

        node_to_length, node_to_path = nx.single_source_dijkstra(G, th_node)
        reachable_nodes = [
            n
            for n in node_to_length.keys()
            if G.nodes[n]['type'] == 'high-peak'
            and not any(
                G.nodes[k]['type'] == 'trailhead' for k in node_to_path[n][1:-1]
            )
        ]

        if reachable_nodes:
            trailheads.append(th_node)

    # After filtering: 76
    sys.stderr.write(f'After filtering: {len(trailheads)}\n')
    trailhead_features = [
        f for f in raw_trailheads if f['properties']['id'] in trailheads
    ]

    # Parking lots can be either nodes or ways
    lots = [
        el
        for el in parking_elements
        if el.get('tags', {}).get('amenity')
        == 'parking'  # exclude nodes that are part of parking ways
        and el['id'] not in spec.invalid_parking_ids
    ]
    lot_nodes = {el['id']: el for el in parking_elements if el['type'] == 'node'}
    id_to_lot = {el['id']: el for el in lots}

    # Found 315 parking lots.
    sys.stderr.write(f'Found {len(lots)} parking lots.\n')

    road_ways = [el for el in road_els if el['type'] == 'way']
    id_to_road_node = {el['id']: el for el in road_els if el['type'] == 'node'}
    node_to_roads = defaultdict(list)
    for el in road_ways:
        for road_node in el['nodes']:
            node_to_roads[road_node].append(el['id'])

    id_to_walkable_node = {}
    id_to_walkable_node.update(id_to_road_node)
    id_to_walkable_node.update(id_to_trail_node)
    id_to_walkable_node.update(lot_nodes)

    # Make a combined road/trail graph
    road_graph = nx.Graph()
    walkable_ways = road_ways + trail_ways
    for way in tqdm(walkable_ways):
        way_id = way['id']
        node_ids = way['nodes']
        nodes = [id_to_walkable_node[n] for n in node_ids]

        for a, b in zip(nodes[:-1], nodes[1:]):
            road_graph.add_edge(
                a['id'],
                b['id'],
                way_id=way_id,
                weight=1000 * haversine(a['lon'], a['lat'], b['lon'], b['lat']),
            )

    # Add parking lots to the graph.
    # For parking lots that are ways,
    #   add all nodes and a connection from the centroid to each node.
    # For parking lots that are nodes, just add the node.
    # If any node is already in the graph, it's connected and we're done.
    # If not, find the closest walkable node for each lot node.
    # This only needs to be done for lots with a centroid within 1km of a trailhead
    hiking_lot_ids = set()
    for el in tqdm(lots):
        lot_loc = element_centroid(el, lot_nodes)
        d = min(
            haversine(*lot_loc, *t['geometry']['coordinates'])
            for t in trailhead_features
        )
        if d > 1:
            # sys.stderr.write(f'Skipping lot {element_link(el)} @ {d:.2f} km\n')
            continue
        # sys.stderr.write(f'Lot {element_link(el)}\n')
        hiking_lot_ids.add(el['id'])

        if el['type'] == 'node':
            nodes = [el]
        else:
            nodes = [lot_nodes[n] for n in el['nodes']]
        nodes_in_graph = [n for n in nodes if road_graph.has_node(n['id'])]
        if nodes_in_graph:
            # if the lot is a node, there's nothing to do.
            if el['type'] == 'way':
                # for a way, add zero-weight connections from the lot to the connected nodes
                for node in nodes_in_graph:
                    road_graph.add_edge(el['id'], node['id'], weight=0)
        else:
            # for each node, find the closest point and add a connection.
            for node in nodes:
                d, graph_node = closest_point_on_trail(
                    (node['lon'], node['lat']), walkable_ways, id_to_walkable_node
                )
                # sys.stderr.write(f'{element_link(node)} to {element_link(graph_node)} @ {d:.0f}m\n')
                road_graph.add_edge(node['id'], graph_node['id'], weight=d)
                if el['type'] == 'way':
                    road_graph.add_edge(el['id'], node['id'], weight=0)

    # Road network: 45529 nodes / 26514 edges
    # Road network: 45739 nodes / 27004 edges
    # Road + Lot network: 370723 nodes / 378994 edges
    nn = road_graph.number_of_nodes()
    ne = road_graph.number_of_edges()
    sys.stderr.write(f'Road + Lot network: {nn} nodes / {ne} edges\n')
    # Found 93 hiking lots.
    sys.stderr.write(f'Found {len(hiking_lot_ids)} hiking lots.\n')

    # How many trailheads have a nearby parking lot?
    num_matched, num_unmatched = 0, 0
    matched_lots = set()
    lot_fs = []
    for trailhead_id in trailheads:
        th = id_to_trailhead[trailhead_id]
        distances = nx.single_source_dijkstra_path_length(
            road_graph, trailhead_id, weight='weight', cutoff=1600
        )
        nearby_lots = [(d, id) for id, d in distances.items() if id in hiking_lot_ids]
        nearby_lots.sort()

        th_txt = node_link(trailhead_id, th['properties'].get('name'))
        if nearby_lots:
            print(th_txt)
            num_matched += 1
            lot_distance_m, lot_id = nearby_lots[0]
            lot = next(
                lot for lot in lots if lot['id'] == lot_id
            )  # could be node or way

            lot_trailhead_path = nx.shortest_path(
                road_graph, lot_id, trailhead_id, weight='weight'
            )
            sys.stderr.write(f'  lot/th walking distance: {lot_distance_m:.2f} m\n')
            is_truncated = False
            if lot['type'] == 'way' and lot_trailhead_path[0] == lot['id']:
                # The way is irrelevant for the walking path; just use the node.
                is_truncated = True
                coord_path = lot_trailhead_path[1:]
            else:
                coord_path = lot_trailhead_path

            matched_lots.add(lot_id)
            path = [
                (id_to_walkable_node[n]['lon'], id_to_walkable_node[n]['lat'])
                for n in coord_path
            ]
            if is_truncated:
                path = [
                    element_centroid(lot, lot_nodes)
                ] + path  # avoid degenerate paths

            assert len(path) >= 2

            d_km = lot_distance_m / 1000
            f = {
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': path,
                },
                'properties': {
                    'type': 'lot-to-trailhead',
                    'from': lot_id,
                    'to': trailhead_id,
                    'trailhead': th,
                    'parking-lot': lot,
                    'nodes': lot_trailhead_path,
                    'd_km': round(d_km, 2),
                    'd_mi': round(d_km * 0.621371, 2),
                },
            }
            lot_fs.append(f)
            print(json.dumps(f))

            # TODO: node/213609657 has an out-and-back path for parking
            # TODO: node/2955316486 has an out-and-back path for parking
        else:
            sys.stderr.write(f'{th_txt}: no nearby lots\n')

    sys.stderr.write(f'{num_matched} trailheads matched, {num_unmatched} unmatched.\n')
    sys.stderr.write('\n')

    for lot_id in matched_lots:
        lot = next(lot for lot in lots if lot['id'] == lot_id)  # could be node or way
        lot_name = id_to_extra_name.get(lot_id)
        if lot_name:
            del id_to_extra_name[lot_id]
        lot_fs.append(
            {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': element_centroid(lot, lot_nodes),
                },
                'properties': {
                    'type': 'parking-lot',
                    'id': lot_id,
                    'url': f'https://www.openstreetmap.org/{lot["type"]}/{lot["id"]}',
                    'name': lot_name,
                    **lot['tags'],
                },
            }
        )

    if id_to_extra_name:
        sys.stderr.write(f'Unclaimed lot names, may be outdated: {id_to_extra_name}\n')

    lot_lot_paths = 0
    for a in tqdm(matched_lots):
        for b in matched_lots:
            if b >= a:
                continue
            lot_lot_d = nx.shortest_path_length(road_graph, a, b, weight='weight')
            if lot_lot_d < 5000:
                d_km = lot_lot_d / 1000
                path = nx.shortest_path(road_graph, a, b, weight='weight')
                nodes_on_path = len([n for n in path if n not in id_to_road_node])
                if nodes_on_path > 0.5 * len(path):
                    sys.stderr.write(f'Tossing out {a} -> {b} as more of a hike.\n')
                    continue
                lot_lot_paths += 1
                lot_fs.append(
                    {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'LineString',
                            'coordinates': [
                                (
                                    (node['lon'], node['lat'])
                                    if node
                                    else element_centroid(id_to_lot[node_id], lot_nodes)
                                )
                                for node_id, node in (
                                    (node, id_to_walkable_node.get(node))
                                    for node in path
                                )
                            ],
                        },
                        'properties': {
                            'type': 'lot-to-lot',
                            'from': a,
                            'to': b,
                            'd_km': round(d_km, 2),
                            'd_mi': round(d_km * 0.621371, 2),
                            'nodes': path,
                        },
                    }
                )

    # Added 31 lot<->lot paths.
    sys.stderr.write(f'Added {lot_lot_paths} lot<->lot paths.\n')

    return lot_fs


if __name__ == '__main__':
    (
        spec_file,
        network_file,
        trails_file,
        roads_file,
        parking_file,
        extra_names_file,
        out_connections,
        out_network,
    ) = sys.argv[1:]

    spec = Spec(json5.load(open(spec_file)))
    features = json.load(open(network_file))['features']
    trails = json.load(open(trails_file))['elements']
    roads = json.load(open(roads_file))['elements']
    parking = json.load(open(parking_file))['elements']
    extra_lot_names = json.load(open(extra_names_file))

    lot_fs = attach_parking(spec, features, trails, parking, roads, extra_lot_names)

    with open(out_connections, 'w') as out:
        json.dump({'type': 'FeatureCollection', 'features': lot_fs}, out)

    with open(out_network, 'w') as out:
        json.dump({'type': 'FeatureCollection', 'features': features + lot_fs}, out)
