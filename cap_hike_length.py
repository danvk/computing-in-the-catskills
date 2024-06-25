"""No hikes longer than X miles."""

import json
import sys

from util import MI_PER_KM


if __name__ == '__main__':
    hikes_file, max_len_mi = sys.argv[1:]
    max_len_km = float(max_len_mi) / MI_PER_KM
    hikes = json.load(open(hikes_file))

    short_hikes = [h for h in hikes if h[0] <= max_len_km]
    sys.stderr.write(f'Keeping {len(short_hikes)} / {len(hikes)} hikes.\n')
    json.dump(short_hikes, sys.stdout, separators=(',', ':'))
