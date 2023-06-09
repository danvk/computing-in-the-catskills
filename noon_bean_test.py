import networkx as nx
from graph import cycle_weight

from noon_bean import gtsp_to_tsp, tsp_solution_to_gtsp
from ort_wrapper import solve_tsp_with_or_tools
from util import rotate_to_start

# This is the graph from the Noon-Bean paper
NB = nx.DiGraph()
NB.add_nodes_from(['a1', 'a2', 'b1', 'b2', 'b3', 'c1', 'c2', 'c3'])
NB.add_edge('a1', 'b3', weight=18)
NB.add_edge('b2', 'a1', weight=42)
NB.add_edge('a2', 'b1', weight=37)
NB.add_edge('b3', 'c2', weight=17)
NB.add_edge('b2', 'c1', weight=23)
NB.add_edge('b1', 'c2', weight=45)
NB.add_edge('b1', 'c3', weight=34)
NB.add_edge('c3', 'a1', weight=51)
NB.add_edge('a2', 'c3', weight=49)
NB.add_edge('c2', 'a1', weight=24)

NB_NODE_SETS = [
    ['a1', 'a2'],
    ['b1', 'b2', 'b3'],
    ['c1', 'c2', 'c3'],
]


def test_gtsp_to_tsp():
    gp = gtsp_to_tsp(NB, NB_NODE_SETS)

    assert NB.nodes() == gp.nodes()
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


def test_tsp_on_transformed_gtsp():
    # cycle = nx.approximation.traveling_salesman_problem(gp)
    cycle = [
        'b3',
        'b1',
        'b2',
        'c2',
        'c3',
        'c1',
        'a1',
        'a2',
        'a1',
        'a2',
        'b3',
        'b1',
        'b2',
        'b3',
    ]
    gtsp_cycle = tsp_solution_to_gtsp(cycle, NB_NODE_SETS)
    print(cycle)
    print(gtsp_cycle)
    assert cycle_weight(NB, gtsp_cycle + [gtsp_cycle[0]]) == 17 + 18 + 24
    assert rotate_to_start(gtsp_cycle, 'a1') == ['a1', 'b3', 'c2']


def test_tsp_with_ortools():
    gp = gtsp_to_tsp(NB, NB_NODE_SETS)
    cycle, cost = solve_tsp_with_or_tools(gp)
    gtsp_cycle = tsp_solution_to_gtsp(cycle, NB_NODE_SETS)
    print(cycle, cost)
    print(gtsp_cycle)
    assert cycle_weight(NB, gtsp_cycle + [gtsp_cycle[0]]) == 17 + 18 + 24
    assert rotate_to_start(gtsp_cycle, 'a1') == ['a1', 'b3', 'c2']
