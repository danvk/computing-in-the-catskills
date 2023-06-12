"""I need to hike a set of peaks. What are my options?

Sample invocation:

    poetry run python peak_planner.py H,BD,TC,C,Pl,Su,W,SW,KHP,Tw,IH,WHP
"""

import json
import sys

from osm import PEAKS
from subset_cover import find_optimal_hikes_subset_cover

if __name__ == '__main__':
    features = json.load(open('data/network+parking.geojson'))['features']
    all_hikes: list[tuple[float, list[int]]] = json.load(open('data/hikes.json'))

    (peaks_to_hike,) = sys.argv[1:]
    ha_code_to_osm_id = {ha_code: osm_id for ha_code, osm_id, _name in PEAKS}
    osm_ids = [ha_code_to_osm_id[ha_code] for ha_code in peaks_to_hike.split(',')]
    print(osm_ids)

    osm_ids_set = set(osm_ids)
    relevant_hikes = [
        h for h in all_hikes if any(peak_id in osm_ids_set for peak_id in h[1])
    ]

    print(f'Unrestricted hikes: {len(relevant_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(
        features, relevant_hikes, osm_ids
    )
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/peak-planner.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    loop_hikes = [(d, nodes) for d, nodes in relevant_hikes if nodes[0] == nodes[-1]]
    print(f'Loop hikes: {len(loop_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, loop_hikes, osm_ids)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/peak-planner-loops-only.geojson', 'w') as out:
        json.dump(fc, out)
