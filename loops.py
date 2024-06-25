#!/usr/bin/env python
"""Find all reasonable loop/out-and-back hikes."""

from collections import defaultdict
from dataclasses import dataclass
import itertools
import json
import math
import sys

import json5
from tqdm import tqdm
import networkx as nx

from graph import make_complete_graph, make_subgraph, read_hiking_graph
from osm import node_link
from spec import Spec
from util import index_by


def log(*args):
    print(*args, file=sys.stderr)


def load_and_index(spec: Spec, raw_features: list):
    # Nix these for now; they really expand the clusters which blows up the problem.
    features = [f for f in raw_features if f['properties'].get('type') != 'lot-to-lot']

    # Add in lot<->lot walks
    for f in raw_features:
        p = f['properties']
        if (
            p.get('type') == 'lot-to-lot'
            and {p['from'], p['to']} not in spec.bad_lot_walks
        ):
            features.append(f)

    G = read_hiking_graph(features)
    peaks = [f for f in features if f['properties'].get('type') == 'high-peak']
    code_to_peak = {f['properties']['code']: f for f in peaks}

    G.remove_edges_from(spec.edges_to_toss)

    # Find connected components of peaks excluding parking lots.
    # If you can only hike from peak A to peak B via a parking lot, that's two hikes.
    G_no_lots = G.copy()
    G_no_lots.remove_nodes_from(
        node for node in G.nodes() if G.nodes[node]['type'] == 'parking-lot'
    )
    log(G.number_of_nodes(), '/', G.number_of_edges())
    log(G_no_lots.number_of_nodes(), '/', G_no_lots.number_of_edges())
    forced_clusters = [
        {code_to_peak[code]['properties']['id'] for code in codes}
        for codes in spec.forced_clusters
    ]
    all_forced = {n for cluster in forced_clusters for n in cluster}
    high_peak_nodes = [n for n in G.nodes() if G.nodes[n]['type'] == 'high-peak']

    G_high_peaks = make_subgraph(G_no_lots, high_peak_nodes)
    log(G_high_peaks.number_of_nodes(), '/', G_high_peaks.number_of_edges())

    peak_components = [
        [n for n in cluster if n not in all_forced]
        for cluster in nx.connected_components(G_high_peaks)
    ]
    peak_components += forced_clusters

    log('# peak components:', len(peak_components))
    log(peak_components)

    # tuple of peaks -> list of parking lots
    peaks_to_lots = defaultdict(list)

    G_lots_peaks = make_subgraph(
        G, [n for n in G.nodes() if G.nodes[n]['type'] in {'high-peak', 'parking-lot'}]
    )

    for peak_component in peak_components:
        # Given the subgraph with this component's peaks and all parking lots,
        # the valid trailhead lots are just the neighbors of the peaks
        # (There will be lot -> lot connections, but we want to exclude these.
        # There will be peak -> peak connections but they're irrelevant.)
        G_lots_component = make_subgraph(
            G_lots_peaks,
            [
                n
                for n in G.nodes()
                if n in peak_component or G.nodes[n]['type'] == 'parking-lot'
            ],
        )
        peaks = tuple(sorted([*peak_component]))
        lots = set()
        for a, b in G_lots_component.edges():
            at = G.nodes[a]['type']
            bt = G.nodes[b]['type']
            if at == 'parking-lot' and bt == 'high-peak':
                lots.add(a)
            elif bt == 'parking-lot' and at == 'high-peak':
                lots.add(b)

        peaks_to_lots[peaks] = [*lots]

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
    # TODO: pick the best loop for any given subset of peaks, not just sequence.
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


@dataclass
class PeakPair:
    d_km: float
    peaks_between: list[int]


def index_peaks(G, peaks):
    GP = make_complete_graph(G, peaks)
    pairs = {}
    for a, b in itertools.combinations(peaks, 2):
        pairs.setdefault(a, {})
        pairs.setdefault(b, {})
        peaks_between = [
            node
            for node in GP.edges[a, b]['path']
            if G.nodes[node]['type'] == 'high-peak' and node != a and node != b
        ]
        pairs[a][b] = pairs[b][a] = PeakPair(
            d_km=GP.edges[a, b]['weight'], peaks_between=peaks_between
        )
    return pairs


def any_surprise_peaks(seq, peak_set, peak_idx):
    for a, b in zip(seq[:-1], seq[1:]):
        for peak in peak_idx[a][b].peaks_between:
            if peak not in peak_set:
                return True
    return False


def plausible_peak_sequences(
    g,
    peaks: list[int],
    peak_idx,
    max_length=100,
    depth=0,
) -> list[tuple[float, tuple[int, ...]]]:
    # zero peaks / single peaks are always a valid sequence
    if max_length == 0:
        return [(0, tuple())]
    sequences: list[tuple[float, tuple[int, ...]]] = [(0, tuple())] + [
        (0, (x,)) for x in peaks
    ]
    if len(peaks) <= 1 or max_length <= 1:
        return sequences

    cache_key = (max_length, tuple(sorted(peaks)))
    result = _cache.get(cache_key)
    if result is not None:
        # log(' ' * depth, f'{peaks} Cache hit (size={len(_cache)})')
        return result

    # You can start and end with any pair of peaks.
    peak_pairs = itertools.combinations(peaks, 2)
    if depth == 0:
        peak_pairs = tqdm([*peak_pairs])
    for start_peak, end_peak in peak_pairs:
        other_peaks = [p for p in peaks if p != start_peak and p != end_peak]
        remaining_seqs = plausible_peak_sequences(
            g, other_peaks, peak_idx, max_length - 2, depth + 1
        )

        # For each set of "inner" peaks, choose the best sequence and eliminate
        # it if it crosses any surprise peaks.
        by_inner_peaks = index_by(remaining_seqs, lambda ds: tuple(sorted(ds[1])))
        # log('by_inner_peaks', by_inner_peaks)
        by_start = peak_idx[start_peak]
        by_end = peak_idx[end_peak]
        for inner_peaks, inner_seqs in by_inner_peaks.items():
            best_d = math.inf
            best_inner_seq = None
            # log('  inner_peaks', inner_peaks)
            # log('  inner_seqs ', inner_seqs)
            if len(inner_peaks) == 0 or max_length == 2:
                best_d = by_start[end_peak].d_km
                best_inner_seq = tuple()
            else:
                for remaining_d, remaining_seq in inner_seqs:
                    # log('    remaining_d  ', remaining_d)
                    # log('    remaining_seq', remaining_seq)
                    start_d = by_start[remaining_seq[0]].d_km
                    end_d = by_end[remaining_seq[-1]].d_km
                    d = start_d + remaining_d + end_d
                    if d < best_d:
                        best_d = d
                        best_inner_seq = remaining_seq
            # Check for surprise peaks
            best_seq = tuple([start_peak, *best_inner_seq, end_peak])
            peak_set = {start_peak, end_peak, *inner_peaks}
            if not any_surprise_peaks(best_seq, peak_set, peak_idx):
                # Exclude paths that go over unexpected peaks.
                # A more stringent check would also exclude paths that go within ~100m
                #  of unexpected peaks.
                sequences.append((best_d, best_seq))

    # Add in the reverse sequences
    sequences += [(d, seq[::-1]) for d, seq in sequences if len(seq) >= 2]

    _cache[cache_key] = sequences
    if depth <= 1:
        log(
            ' ' * depth,
            f'Completed {peaks} ({len(sequences)} seqs), cache size={len(_cache)}',
        )
    return sequences


if __name__ == '__main__':
    spec_file, network_file = sys.argv[1:]
    spec = Spec(json5.load(open(spec_file)))
    features = json.load(open(network_file))['features']
    G, peaks_to_lots = load_and_index(spec, features)

    for peaks, lots in sorted(peaks_to_lots.items(), key=lambda x: len(x[1])):
        log('Lots:', len(lots), lots, 'Peaks:', len(peaks), peaks)
        for peak in peaks:
            log('  ', node_link(peak, G.nodes[peak]['feature']['properties']['name']))
    log(len(peaks_to_lots), 'connected clusters of peaks.')

    # 10 peaks / 20 lots
    # 10 peaks / 8 lots
    log('')
    hikes = []
    num_loops = 0
    num_thrus = 0

    for peaks, lots in tqdm(peaks_to_lots.items()):
        log(len(peaks), peaks, len(lots), lots)
        peak_idx = index_peaks(G, peaks)
        # Lot->Lot hikes are not interesting
        _cache = {}
        plausible_seqs = [
            p
            for p in plausible_peak_sequences(G, list(peaks), peak_idx, max_length=8)
            if p[1]
        ]
        log(f'  plausible sequences: {len(plausible_seqs)}')
        loops = loop_hikes_for_peak_seq(G, lots, peaks, plausible_seqs)
        thrus = through_hikes_for_peak_seq(G, lots, peaks, plausible_seqs)
        hikes += loops
        hikes += thrus
        log(f'  loops: {len(loops)}, thru: {len(thrus)}')
        num_loops += len(loops)
        num_thrus += len(thrus)

    hikes = [(round(d_km, 3), nodes) for d_km, nodes in hikes]

    json.dump(hikes, sys.stdout, separators=(',', ':'))

    log(f'Loops: {num_loops}')
    log(f'Thrus: {num_thrus}')
    log(f'Total hikes: {num_loops + num_thrus}')

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
