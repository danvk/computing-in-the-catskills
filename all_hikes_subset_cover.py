import json
import sys

from subset_cover import find_optimal_hikes_subset_cover


if __name__ == '__main__':
    network_file, hikes_file = sys.argv[1:]
    features = json.load(open(network_file))['features']
    all_hikes: list[tuple[float, list[int]]] = json.load(open(hikes_file))

    print(f'Unrestricted hikes: {len(all_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, all_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/unrestricted.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    loop_hikes = [(d, nodes) for d, nodes in all_hikes if nodes[0] == nodes[-1]]
    print(f'Loop hikes: {len(loop_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, loop_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/loops-only.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    day_hikes = [(d, nodes) for d, nodes in all_hikes if d < 21]  # 21km = ~13 miles
    print(f'Day hikes: {len(day_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, day_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/day-hikes-only.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    day_loop_hikes = [
        (d, nodes) for d, nodes in loop_hikes if d < 21
    ]  # 21km = ~13 miles
    print(f'Day loop hikes: {len(day_loop_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, day_loop_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/day-loop-hikes-only.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    penalized_hikes = [
        (d + (0 if nodes[0] == nodes[-1] else 3.5), nodes, d) for d, nodes in all_hikes
    ]
    print(f'Preferred loop hikes: {len(day_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, penalized_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/prefer-loop-hikes.geojson', 'w') as out:
        json.dump(fc, out)

    print()
    penalized_day_hikes = [
        (cost, nodes, d_km) for cost, nodes, d_km in penalized_hikes if d_km < 21
    ]
    print(f'Preferred loop day hikes: {len(penalized_day_hikes)}')
    d_km, chosen, fc = find_optimal_hikes_subset_cover(features, penalized_day_hikes)
    print(f'  {len(chosen)} hikes: {d_km:.2f} km = {d_km * 0.621371:.2f} mi')
    with open('data/day-prefer-loop-hikes.geojson', 'w') as out:
        json.dump(fc, out)
