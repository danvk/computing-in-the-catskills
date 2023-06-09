"""Pythonic wrapper around Google's OR Tools TSP."""

import networkx as nx

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def solve_tsp_with_or_tools(g: nx.Graph, time_limit_secs=30) -> list:
    nodes = [*g.nodes()]
    manager = pywrapcp.RoutingIndexManager(len(nodes), 1, 0)
    routing = pywrapcp.RoutingModel(manager)
    penalty = len(nodes) * max(w for _a, _b, w in g.edges.data('weight'))
    for a, b, d in g.edges.data('weight'):
        assert d == int(d), f'edges must have integer weights ({a}->{b}={d})'

    def distance_callback(from_index, to_index):
        from_node = nodes[manager.IndexToNode(from_index)]
        to_node = nodes[manager.IndexToNode(to_index)]
        # OR Tools silently reinterprets exceptions as "return 0!"
        # https://github.com/google/or-tools/issues/3224
        if g.has_edge(from_node, to_node):
            d = g.edges[from_node, to_node]['weight']
            return d
        return penalty

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = time_limit_secs
    search_parameters.log_search = True
    solution = routing.SolveWithParameters(search_parameters)
    print('status', routing.status(), not not solution)

    solution_weight = 0
    index = routing.Start(0)
    solution_seq = []
    while not routing.IsEnd(index):
        previous_index = index
        solution_seq.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
        solution_weight += routing.GetArcCostForVehicle(previous_index, index, 0)
    solution_seq.append(manager.IndexToNode(routing.Start(0)))
    solution_nodes = [nodes[i] for i in solution_seq]
    print(solution_seq)
    print(solution_nodes)

    return solution_nodes, solution_weight
