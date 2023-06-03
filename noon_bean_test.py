import networkx as nx

from noon_bean import gtsp_to_tsp


def test_gtsp_to_tsp():
    g = nx.DiGraph()
    g.add_nodes_from(['a1', 'a2', 'b1', 'b2', 'b3', 'c1', 'c2', 'c3'])
    g.add_edge('a1', 'b3', weight=18)
    g.add_edge('b2', 'a1', weight=42)
    g.add_edge('a2', 'b1', weight=37)
    g.add_edge('b3', 'c2', weight=17)
    g.add_edge('b2', 'c1', weight=23)
    g.add_edge('b1', 'c2', weight=45)
    g.add_edge('b1', 'c3', weight=34)
    g.add_edge('c3', 'a1', weight=51)
    g.add_edge('a2', 'c3', weight=49)
    g.add_edge('c2', 'a1', weight=24)

    gp = gtsp_to_tsp(g, [
        ['a1', 'a2'],
        ['b1', 'b2', 'b3'],
        ['c1', 'c2', 'c3'],
    ])

    assert g.nodes() == gp.nodes()
    # intra-cluster cycles
    assert gp.edges['c1', 'c2']['weight'] == 0
    assert gp.edges['c2', 'c3']['weight'] == 0
    assert gp.edges['c3', 'c1']['weight'] == 0
    assert gp.edges['b1', 'b2']['weight'] == 0
    assert gp.edges['b2', 'b3']['weight'] == 0
    assert gp.edges['b3', 'b1']['weight'] == 0
    assert gp.edges['a1', 'a2']['weight'] == 0
    assert gp.edges['a2', 'a1']['weight'] == 0

    # shifted inter-cluster edges
    assert gp.edges['a2', 'b3']['weight'] == 341 + 18
    assert gp.edges['c1', 'a1']['weight'] == 341 + 24
    assert gp.edges['b2', 'c2']['weight'] == 341 + 17
    assert gp.edges['a1', 'c3']['weight'] == 341 + 49
    assert gp.edges['c2', 'a1']['weight'] == 341 + 51
