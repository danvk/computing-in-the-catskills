import networkx as nx

def make_complete_graph(G, nodes, weight='weight'):
    dist = {}
    path = {}
    for n, (d, p) in nx.all_pairs_dijkstra(G, weight=weight):
        dist[n] = d
        path[n] = p

    GG = nx.Graph()
    for u in nodes:
        for v in nodes:
            if u == v:
                continue
            GG.add_edge(u, v, weight=dist[u][v], path=path[u][v])
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


def read_hiking_graph(features) -> nx.Graph:
    peak_features = [f for f in features if f['properties'].get('type') == 'high-peak']
    id_to_peak = {f['properties']['id']: f for f in peak_features}
    id_to_trailhead = {f['properties']['id']: f for f in features if f['properties'].get('type') == 'trailhead'}

    G = nx.Graph()
    for f in features:
        if f['geometry']['type'] != 'LineString':
            continue
        nodes = f['properties']['nodes']
        for node in nodes[1:-1]:
            assert node not in id_to_peak and node not in id_to_trailhead
        a, b = nodes[0], nodes[-1]
        d_km = f['properties']['d_km']
        G.add_edge(a, b, weight=d_km, feature=f)

    for n in G.nodes():
        if n in id_to_peak:
            G.nodes[n]['type'] = 'high-peak'
        elif n in id_to_trailhead:
            G.nodes[n]['type'] = 'trailhead'
        else:
            G.nodes[n]['type'] = 'junction'

    return G, id_to_peak, id_to_trailhead
