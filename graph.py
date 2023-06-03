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
