import json
import sys

from subset_cover import find_optimal_hikes_subset_cover
from util import MI_PER_KM, Timer


if __name__ == '__main__':
    network_file, hikes_file, max_day_hike_mi_str, max_iters_str = sys.argv[1:]
    max_iters = int(max_iters_str)
    max_day_hike_mi = float(max_day_hike_mi_str)
    max_day_hike_km = max_day_hike_mi / MI_PER_KM
    features = json.load(open(network_file))['features']
    all_hikes: list[tuple[float, list[int]]] = json.load(open(hikes_file))

    print(f'Max iterations: {max_iters}')
    print(f'Max day hike length: {max_day_hike_mi} mi')

    # 30 mi hard cap
    # TODO: make this a flag
    all_hikes = [(d, ele, seq) for d, ele, seq in all_hikes if d < 30 / MI_PER_KM]

    # TODO: make this a flag
    non_loop_penalty_km = 3.5

    loop_hikes = [
        (d, ele, nodes) for d, ele, nodes in all_hikes if nodes[0] == nodes[-1]
    ]
    print(f'Loop hikes: {len(loop_hikes)}')
    with Timer():
        d_km, chosen, fc = find_optimal_hikes_subset_cover(
            features, loop_hikes, maxiters=max_iters
        )
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * MI_PER_KM:.2f} mi')
    with open('data/hikes/loops-only.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    day_hikes = [(d, ele, nodes) for d, ele, nodes in all_hikes if d < max_day_hike_km]
    print(f'Day hikes: {len(day_hikes)}')
    with Timer():
        d_km, chosen, fc = find_optimal_hikes_subset_cover(
            features, day_hikes, maxiters=max_iters
        )
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * MI_PER_KM:.2f} mi')
    with open('data/hikes/day-hikes-only.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    day_loop_hikes = [
        (d, ele, nodes) for d, ele, nodes in loop_hikes if d < max_day_hike_km
    ]
    print(f'Day loop hikes: {len(day_loop_hikes)}')
    with Timer():
        d_km, chosen, fc = find_optimal_hikes_subset_cover(
            features, day_loop_hikes, maxiters=max_iters
        )
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * MI_PER_KM:.2f} mi')
    with open('data/hikes/day-loop-hikes-only.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    penalized_hikes = [
        (d + (0 if nodes[0] == nodes[-1] else non_loop_penalty_km), ele, nodes, d)
        for d, ele, nodes in all_hikes
    ]
    print(f'Preferred loop hikes: {len(day_hikes)}')
    with Timer():
        d_km, chosen, fc = find_optimal_hikes_subset_cover(
            features, penalized_hikes, maxiters=max_iters
        )
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * MI_PER_KM:.2f} mi')
    with open('data/hikes/prefer-loop-hikes.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    penalized_day_hikes = [
        (cost, ele, nodes, d_km)
        for cost, ele, nodes, d_km in penalized_hikes
        if d_km < max_day_hike_km
    ]
    print(f'Preferred loop day hikes: {len(penalized_day_hikes)}')
    with Timer():
        d_km, chosen, fc = find_optimal_hikes_subset_cover(
            features, penalized_day_hikes, maxiters=max_iters
        )
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * MI_PER_KM:.2f} mi')
    with open('data/hikes/day-prefer-loop-hikes.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    print(f'Unrestricted hikes: {len(all_hikes)}')
    with Timer():
        d_km, chosen, fc = find_optimal_hikes_subset_cover(
            features, all_hikes, maxiters=max_iters
        )
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * MI_PER_KM:.2f} mi')
    with open('data/hikes/unrestricted.geojson', 'w') as out:
        json.dump(fc, out)
