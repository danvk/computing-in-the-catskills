#!/usr/bin/env python
"""Write out nodes for high peaks that are on trails.

OSM is a bit too precise about the location of peaks for our needs.
This script shifts the peaks to use nearby nodes that are on trails.
"""

from collections import Counter, defaultdict
import json

from osm import OsmElement, OsmNode, closest_point_on_trail

peak_nodes: list[OsmNode] = json.load(open('data/peaks-3500.json'))['elements']
assert len(peak_nodes) == 33

alternate_peak_nodes: list[OsmNode] = json.load(open('data/alternate-peaks.json'))[
    'elements'
]
assert len(alternate_peak_nodes) == 4
for node in alternate_peak_nodes:
    node['tags']['alternate'] = True

peak_nodes += alternate_peak_nodes

trail_elements: list[OsmElement] = json.load(open('data/combined-trails.json'))[
    'elements'
]
node_to_trails = defaultdict(list)
trail_ways = [el for el in trail_elements if el['type'] == 'way']
for el in trail_ways:
    for node in el['nodes']:
        node_to_trails[node].append(el['id'])
trail_nodes = {el['id']: el for el in trail_elements if el['type'] == 'node'}


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
        new_peaks.append(peak)
        continue

    pt_m, pt_node = closest_point_on_trail(
        (peak['lon'], peak['lat']), trail_ways, trail_nodes
    )
    if pt_m < 53:  # The Mill Brook Ridge peak node is 52.6m from the trail.
        pt_node['tags'] = {
            **peak['tags'],
            'original_node': peak_id,
            'original_d_m': round(pt_m, 2),
            'connected': True,
        }
        new_peaks.append(pt_node)
        continue

    # Must be an un-trailed peak; leave it as-is.
    peak['tags']['connected'] = False
    new_peaks.append(peak)
    print(f'Disconnected peak ({pt_m} m from {pt_node}): {peak}')

counts = Counter(peak['tags']['connected'] for peak in new_peaks)

print('Peaks:')
print(f' Connected: {counts[True]}')
print(f' Disconnected: {counts[False]}')

assert len(new_peaks) == 33 + 4
with open('data/peaks-connected.json', 'w') as out:
    json.dump(
        {
            'elements': new_peaks,
        },
        out,
        indent=2,
    )
