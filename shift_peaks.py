#!/usr/bin/env python
"""Write out nodes for high peaks that are on trails.

OSM is a bit too precise about the location of peaks for our needs.
This script shifts the peaks to use nearby nodes that are on trails.
"""

import sys
import json
from collections import Counter, defaultdict

from osm import OsmElement, OsmNode, closest_point_on_trail, element_link, way_length


def shift_peaks(peaks_file: str, trails_file: str):
    peak_nodes: list[OsmNode] = json.load(open(peaks_file))['elements']

    trail_elements: list[OsmElement] = json.load(open(trails_file))['elements']
    node_to_trails = defaultdict(list)
    trail_ways = [el for el in trail_elements if el['type'] == 'way']
    for el in trail_ways:
        for node in el['nodes']:
            node_to_trails[node].append(el['id'])
    trail_nodes = {el['id']: el for el in trail_elements if el['type'] == 'node'}

    trail_end_nodes = Counter()
    for way in trail_ways:
        trail_end_nodes[way['nodes'][0]] += 1
        trail_end_nodes[way['nodes'][-1]] += 1

    # Remove ways that are short (less than 100m) and not attached to the end of another
    # way. This removes the option of narrowly bypassing a peak without bagging it,
    # which greatly reduces the number of possible hikes later.
    new_ways = []
    for way in trail_ways:
        nodes = way['nodes']
        if way_length(nodes, trail_nodes) < 0.1:
            start = trail_end_nodes[nodes[0]]
            end = trail_end_nodes[nodes[-1]]
            if start == 1 and end == 1:
                print(f'Dropping {element_link(way)}')
                continue
        new_ways.append(way)

    trail_ways = new_ways

    on_trail = 0
    farthest = 0

    new_peaks: list[OsmNode] = []
    for peak in peak_nodes:
        name = peak['tags']['name']
        peak_id = peak['id']

        if name == 'Vly Mountain':
            # OSM's point for this peak is considerably east of the canister.
            # This shifts it closer to the end of the herd path.
            peak['lat'] = 42.24588
            peak['lon'] = -74.44845

        trails = node_to_trails.get(peak_id)
        if trails:
            # This peak node coincides with a trail node. Keep it as-is.
            peak['tags']['connected'] = True
            sys.stderr.write(f'{name} is a node on a trail\n')
            on_trail += 1
            new_peaks.append(peak)
            continue

        pt_m, pt_node = closest_point_on_trail(
            (peak['lon'], peak['lat']), trail_ways, trail_nodes
        )
        farthest = max(pt_m, farthest)

        # The Mill Brook Ridge peak node is 52.6m from the trail.
        # The Friday peak node is 61.86m from the OSM herd path
        if pt_m < 62:
            pt_node['tags'] = {
                **peak['tags'],
                'original_node': peak_id,
                'original_d_m': round(pt_m, 2),
                'connected': True,
            }
            sys.stderr.write(f'{name} is only {pt_m:.3g}m from a trail\n')
            new_peaks.append(pt_node)
            continue

        # Must be an un-trailed peak; leave it as-is.
        peak['tags']['connected'] = False
        new_peaks.append(peak)
        sys.stderr.write(f'Disconnected peak ({pt_m} m from {pt_node}): {peak}\n')

    counts = Counter(peak['tags']['connected'] for peak in new_peaks)

    sys.stderr.write('Peaks:\n')
    sys.stderr.write(f' Connected: {counts[True]}\n')
    sys.stderr.write(f' Disconnected: {counts[False]}\n')

    sys.stderr.write(f'On trail: {on_trail}\n')
    sys.stderr.write(f'Farthest from trail: {farthest:.2f} m\n')

    assert len(new_peaks) == len(peak_nodes)

    return new_peaks


if __name__ == '__main__':
    peaks_file, trails_file = sys.argv[1:]
    # peaks_file = 'data/peaks-3500.json'
    # trails_file = 'data/combined-trails.json'
    new_peaks = shift_peaks(peaks_file, trails_file)
    json.dump(
        {
            'elements': new_peaks,
        },
        sys.stdout,
        indent=2,
    )
