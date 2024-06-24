import itertools

import networkx as nx


def make_complete_graph(G, nodes, weight='weight'):
    dist = {}
    path = {}
    for n in nodes:
        d, p = nx.single_source_dijkstra(G, n, weight=weight)
        dist[n] = d
        path[n] = p

    GG = nx.Graph()
    for u in nodes:
        for v in nodes:
            if u == v:
                continue
            try:
                GG.add_edge(u, v, weight=dist[u][v], path=path[u][v])
            except KeyError as e:
                print(f'Missing {u} {v}')
                raise e
    return GG


def make_subgraph(G: nx.Graph, nodes):
    # This is what I thought G.subgraph would do, but I guess I don't understand that!
    # This makes no attempts to preserve weights/paths, just connectivity
    nodes_set = set(nodes)
    to_remove = [n for n in G.nodes() if n not in nodes_set]
    GG = G.copy()
    for node in to_remove:
        # Remove node, adding direct connections between all its neighbors
        ns = nx.neighbors(GG, node)
        GG.add_edges_from(itertools.combinations(ns, 2))
        GG.remove_node(node)

    return GG


def cycle_weight(G, nodes, weight='weight'):
    total_weight = 0
    for a, b in zip(nodes[:-1], nodes[1:]):
        total_weight += G.edges[a, b][weight]
    return total_weight


def scale_graph(g, factor):
    """Scale up edge weights by the factor and round them to integers."""
    scaled_g = g.copy()
    for a, b, w in g.edges.data('weight'):
        scaled_g.edges[a, b]['weight'] = int(round(w * factor))
    return scaled_g


def get_index_for_type(features: list, type: str) -> dict[int, any]:
    type_features = [f for f in features if f['properties'].get('type') == type]
    return {f['properties']['id']: f for f in type_features}


def get_peak_index(features: list):
    return get_index_for_type(features, 'high-peak')


def get_lot_index(features: list):
    return get_index_for_type(features, 'parking-lot')


def get_trailhead_index(features: list):
    return get_index_for_type(features, 'trailhead')


def read_hiking_graph(
    features,
) -> nx.Graph:
    id_to_peak = get_peak_index(features)
    id_to_feature = {
        f['properties']['id']: f for f in features if 'id' in f['properties']
    }

    G = nx.Graph()
    for f in features:
        if f['geometry']['type'] != 'LineString':
            continue
        nodes = f['properties']['nodes']
        for node in nodes[1:-1]:
            assert node not in id_to_peak  # and node not in id_to_lot
        a, b = nodes[0], nodes[-1]
        d_km = f['properties']['d_km']
        G.add_edge(a, b, weight=d_km, feature=f)

    for n in G.nodes():
        f = id_to_feature[n]
        G.nodes[n]['feature'] = f
        p = f.get('properties', {})
        G.nodes[n]['type'] = p.get('type', 'junction')

    return G
