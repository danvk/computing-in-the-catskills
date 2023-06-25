#!/usr/bin/env python
"""Find all reasonable loop/out-and-back hikes."""

from collections import defaultdict
import itertools
import json
import math

from tqdm import tqdm
import networkx as nx

from graph import make_complete_graph, read_hiking_graph
from util import index_by

bad_lot_walks = [
    {1273010086, 1273001263},
    {9217245722, 1273010086},
    {385488241, 385488236},
    {385488238, 385488236},
]


def load_and_index(raw_features: list):
    # Nix these for now; they really expand the clusters which blows up the problem.
    features = [f for f in raw_features if f['properties'].get('type') != 'lot-to-lot']

    # Very carefully add in lot<->lot walks
    # ok_lot_walks = [
    #    {10942786419, 2947971907},  # Burnam / McKinley Hollow
    #    {1075850833, 995422357},  # Spruceton / Diamond Notch
    # ]
    for f in raw_features:
        p = f['properties']
        if p.get('type') == 'lot-to-lot' and {p['from'], p['to']} not in bad_lot_walks:
            features.append(f)

    G = read_hiking_graph(features)

    lot_to_peaks = {}
    peaks_to_lots = defaultdict(list)

    for lot_node in G.nodes():
        if G.nodes[lot_node]['type'] != 'parking-lot':
            continue

        # Get the reachable set of non-trailhead nodes from this trailhead
        node_to_length, node_to_path = nx.single_source_dijkstra(G, lot_node)
        reachable_nodes = [
            n for n in node_to_length.keys() if G.nodes[n]['type'] == 'high-peak'
        ]

        if not reachable_nodes:
            print(f'Filtered out lot {lot_node}')
            continue

        reachable_nodes.sort()
        reachable_nodes = tuple(reachable_nodes)
        lot_to_peaks[lot_node] = reachable_nodes
        peaks_to_lots[reachable_nodes].append(lot_node)

    return G, peaks_to_lots


def through_hikes_for_peak_seq(g, lots, peaks, peak_seqs):
    peaks = list(peaks)
    lots = list(lots)
    if len(lots) == 1:
        return []  # No through hikes with only one lot
    hikes = []
    gp = make_complete_graph(g, peaks + lots)
    for peak_seq_d, peak_seq in peak_seqs:
        best_d = math.inf
        best_cycle = None
        for lot1, lot2 in itertools.product(lots, lots):
            if lot1 == lot2:
                continue  # we'll handle loops separately

            d = (
                gp.edges[lot1, peak_seq[0]]['weight']
                + peak_seq_d
                + gp.edges[peak_seq[-1], lot2]['weight']
            )
            if d < best_d:
                best_d = d
                best_cycle = [lot1, *peak_seq, lot2]
        all_peaks = {
            node
            for a, b in zip(best_cycle[:-1], best_cycle[1:])
            for node in gp.edges[a, b]['path']
            if g.nodes[node]['type'] == 'high-peak'
        }
        if len(all_peaks) == len(peak_seq):
            # Exclude paths that go over unexpected peaks.
            # A more stringent check would also exclude paths that go within ~100m of
            # unexpected peaks.
            hikes.append((best_d, best_cycle))

    return hikes


def loop_hikes_for_peak_seq(g, lots, peaks, peak_seqs):
    peaks = list(peaks)
    lots = list(lots)
    hikes = []
    gp = make_complete_graph(g, peaks + lots)
    for peak_seq_d, peak_seq in peak_seqs:
        best_d = math.inf
        best_cycle = None
        for lot in lots:
            d = (
                gp.edges[lot, peak_seq[0]]['weight']
                + peak_seq_d
                + gp.edges[peak_seq[-1], lot]['weight']
            )
            if d < best_d:
                best_d = d
                best_cycle = [lot, *peak_seq, lot]
        all_peaks = {
            node
            for a, b in zip(best_cycle[:-1], best_cycle[1:])
            for node in gp.edges[a, b]['path']
            if g.nodes[node]['type'] == 'high-peak'
        }
        if len(all_peaks) == len(peak_seq):
            # Exclude paths that go over unexpected peaks.
            # A more stringent check would also exclude paths that go within ~100m of
            # unexpected peaks.
            hikes.append((best_d, best_cycle))

    return hikes


_cache = {}


def plausible_peak_sequences(
    g, peaks: list[int]
) -> list[tuple[float, tuple[int, ...]]]:
    sequences = []
    peaks = list(peaks)

    # zero peaks / single peaks are always a valid sequence
    sequences: list[tuple[float, tuple[int, ...]]] = [(0, tuple())] + [
        (0, (x,)) for x in peaks
    ]
    if len(peaks) <= 1:
        return sequences

    cache_key = tuple(sorted(peaks))
    result = _cache.get(cache_key)
    if result is not None:
        return result

    # TODO: would be really nice to eliminate this call!
    gp = make_complete_graph(g, peaks)

    # You can start and end with any pair of peaks.
    for start_peak, end_peak in itertools.product(peaks, peaks):
        if start_peak == end_peak:
            continue  # TODO: require start_peak < end_peak as an optimization
        other_peaks = [p for p in peaks if p != start_peak and p != end_peak]
        # might be more efficient (but tricky) to pass down gp here rather than g.
        remaining_seqs = plausible_peak_sequences(g, other_peaks)

        # For each set of "inner" peaks, choose the best sequence and eliminate
        # it if it crosses any surprise peaks.
        by_inner_peaks = index_by(remaining_seqs, lambda ds: tuple(sorted(ds[1])))
        # print('by_inner_peaks', by_inner_peaks)
        for inner_peaks, inner_seqs in by_inner_peaks.items():
            best_d = math.inf
            best_inner_seq = None
            # print('  inner_peaks', inner_peaks)
            # print('  inner_seqs ', inner_seqs)
            if len(inner_peaks) == 0:
                best_d = gp.edges[start_peak, end_peak]['weight']
                best_inner_seq = tuple()
            else:
                for remaining_d, remaining_seq in inner_seqs:
                    # print('    remaining_d  ', remaining_d)
                    # print('    remaining_seq', remaining_seq)
                    start_d = gp.edges[start_peak, remaining_seq[0]]['weight']
                    end_d = gp.edges[remaining_seq[-1], end_peak]['weight']
                    d = start_d + remaining_d + end_d
                    if d < best_d:
                        best_d = d
                        best_inner_seq = remaining_seq
            # Check for surprise peaks
            best_seq = tuple([start_peak, *best_inner_seq, end_peak])
            all_peaks = {
                node
                for a, b in zip(best_seq[:-1], best_seq[1:])
                for node in gp.edges[a, b]['path']
                if g.nodes[node]['type'] == 'high-peak'
            }
            if len(all_peaks) == len(best_seq):
                # Exclude paths that go over unexpected peaks.
                # A more stringent check would also exclude paths that go within ~100m
                #  of unexpected peaks.
                sequences.append((best_d, best_seq))

    _cache[cache_key] = sequences
    return sequences


# Want to capture the idea that a "bowtie" hike should really be done as two loops.


if __name__ == '__main__':
    G, peaks_to_lots = load_and_index(
        json.load(open('data/network+parking.geojson'))['features']
    )

    for peaks, lots in sorted(peaks_to_lots.items(), key=lambda x: len(x[1])):
        print(len(lots), lots, len(peaks), peaks)
    print(len(peaks_to_lots), 'connected clusters of peaks.')

    # 10 peaks / 20 lots
    # 10 peaks / 8 lots
    print('')
    hikes = []
    num_loops = 0
    num_thrus = 0
    for peaks, lots in tqdm(peaks_to_lots.items()):
        print(len(peaks), peaks, len(lots), lots)
        # Lot->Lot hikes are not interesting
        plausible_seqs = [p for p in plausible_peak_sequences(G, peaks) if p[1]]
        print(f'  plausible sequences: {len(plausible_seqs)}')
        loops = loop_hikes_for_peak_seq(G, lots, peaks, plausible_seqs)
        thrus = through_hikes_for_peak_seq(G, lots, peaks, plausible_seqs)
        hikes += loops
        hikes += thrus
        print(f'  loops: {len(loops)}, thru: {len(thrus)}')
        num_loops += len(loops)
        num_thrus += len(thrus)

    with open('data/hikes.json', 'w') as out:
        json.dump(hikes, out)

    print(f'Loops: {num_loops}')
    print(f'Thrus: {num_thrus}')
    print(f'Total hikes: {num_loops + num_thrus}')

"""
This is the group of 12:
https://openstreetmap.org/node/1938215682, SW Hunter
https://openstreetmap.org/node/2882649917, Plateau
https://openstreetmap.org/node/1938201532, Hunter
https://openstreetmap.org/node/2882649730, Sugarloaf
https://openstreetmap.org/node/7982977638, Twin
https://openstreetmap.org/node/2955311547, Westkill
https://openstreetmap.org/node/10033501291, Rusk
https://openstreetmap.org/node/7978185605, Indian Head
https://openstreetmap.org/node/357574030, North Dome
https://openstreetmap.org/node/10010091368, Sherrill
https://openstreetmap.org/node/9785950126, Kaaterskill
https://openstreetmap.org/node/357563196, Halcott

9147145385 = Panther
[1938215682, 2882649917, 1938201532, 2882649730, 7982977638, 2955311547, 10033501291,
7978185605, 357574030, 10010091368]
"""
