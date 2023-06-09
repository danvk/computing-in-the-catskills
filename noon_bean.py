"""Implementation of the Noon-Beam transform from GTSP -> TSP.

https://www.researchgate.net/publication/265366022
"""

import itertools

import networkx as nx


def gtsp_to_tsp(
    g: nx.DiGraph,
    node_sets: list[list],
    big_val=None,
) -> nx.DiGraph:
    """Construct a graph on which to run asymmetric TSP using the Noon-Bean algorithm"""
    # Verify preconditions:
    # - node_sets is disjoint sets whose union is the full set of nodes
    # - There are no edges within a node_set
    all_nodes = set().union(*node_sets)
    assert len(all_nodes) == g.number_of_nodes()
    for a, b in itertools.combinations(node_sets, 2):
        assert set(a).isdisjoint(set(b))

    node_to_idx = {node: i for i, node_set in enumerate(node_sets) for node in node_set}

    for a, b, d in g.edges(data=True):
        assert node_to_idx[a] != node_to_idx[b], f'Intra-cluster edge from {a}->{b}'
        assert 'weight' in d
        # print(a, b, d['weight'])

    sum_weight = sum(w for _a, _b, w in g.edges.data('weight'))
    print('sum_weight=', sum_weight)
    if big_val is None:
        big_val = 1 + sum_weight

    gt = nx.DiGraph()
    gt.add_nodes_from(all_nodes)

    # Add zero-weight intra-cluster cycles
    for node_set in node_sets:
        n = len(node_set)
        if n == 1:
            continue
        for i, a in enumerate(node_set):
            b = node_set[(i + 1) % n]
            gt.add_edge(a, b, weight=0)

    # Add intra-cluster edges to previous node's in the cycle with a greater weight.
    for a, b, weight in g.edges.data('weight'):
        node_set = node_sets[node_to_idx[a]]
        ai = node_set.index(a)
        n = len(node_set)
        preva = node_set[(ai - 1 + n) % n]
        gt.add_edge(preva, b, weight=weight + big_val)

    return gt


def tsp_solution_to_gtsp(
    cycle: list,
    node_sets: list[list],
) -> list:
    """Map a solution to TSP back onto a solution to the GTSP."""
    node_to_idx = {node: i for i, node_set in enumerate(node_sets) for node in node_set}
    gtsp_cycle = []
    for a, b in zip(cycle[:-1], cycle[1:]):
        i = node_to_idx[a]
        j = node_to_idx[b]
        if i == j:
            continue  # ignore intra-cluster edges
        gtsp_cycle.append(b)

    return gtsp_cycle
