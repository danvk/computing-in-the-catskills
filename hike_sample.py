"""Extract a single hike from hikes.json and produce a GeoJSON FeatureCollection on stdout"""

import argparse
import json
import random
import sys

from formatting import geojson_for_hike, gpx_for_hike

from osm import node_link


parser = argparse.ArgumentParser(
    prog='Hike Sampler',
    description='Extract hikes for visualization, either as GeoJSON or GPX',
)
parser.add_argument('--format', choices=['geojson', 'gpx'], default='geojson')
parser.add_argument('--seq', help='Comma-separated list of lot/peak IDs')
parser.add_argument('network_file', help='Path to network.geojson file')
parser.add_argument('hikes_file', help='Path to hikes+ele.json file')


if __name__ == '__main__':
    args = parser.parse_args()

    features = json.load(open(args.network_file))['features']
    if args.seq:
        d_km = 0
        loop = [int(x) for x in args.seq.split(',')]
    else:
        all_hikes: list[tuple[float, list[int]]] = json.load(open(args.hikes_file))
        # all_hikes = [(d, ele, seq) for d, ele, seq in all_hikes if d < 30 / 0.621371]
        sys.stderr.write(f'Considering {len(all_hikes)} hikes.\n')

        hike = random.choice(all_hikes)
        d_km, gain_m, loop = hike
        gain_ft = int(gain_m * 3.28084)
        sys.stderr.write(
            f'Random hike: {d_km:.2f} km = {d_km * 0.621371:.2f} mi, +{gain_ft}ft\n'
        )
        sys.stderr.write('--seq {",".join(loop)}\n')
        for peak in loop:
            sys.stderr.write(f'  {node_link(peak)}\n')

        # sys.stderr.write(f'Calculated elevation gain: {ele_m} m = {ele_m*3.28084:.2f}ft\n')

    if args.format == 'geojson':
        json.dump(geojson_for_hike(features, d_km, loop), sys.stdout)
    elif args.format == 'gpx':
        print(gpx_for_hike(features, d_km, loop))
