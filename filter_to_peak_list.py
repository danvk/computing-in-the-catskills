#!/usr/bin/env python
"""Filter Overpass results by a list of GNIS Feature IDs for high peaks.

Format of text file is tab-delimted, columns are proprietary code, GNIS ID, ...
If none of the nodes have that GNIS ID, it will search the wikidata and then name tags.
"""

import json
import sys


def run(osm_file: str, peaks_file: str):
    osm = json.load(open(osm_file))

    gnis_to_code = {}
    with open(peaks_file) as f:
        for line in f:
            if line.startswith('#'):
                continue
            code, gnis_id = line.strip().split('\t')[:2]
            gnis_to_code[gnis_id] = code

    out_els = []
    for field in ('gnis:feature_id', 'wikidata', 'name'):
        for el in osm['elements']:
            tags = el['tags']
            if 'code' in tags:
                continue
            gnis_id = tags.get(field)
            if gnis_id and gnis_id in gnis_to_code:
                tags['code'] = gnis_to_code[gnis_id]
                out_els.append(el)
                del gnis_to_code[gnis_id]

    assert len(gnis_to_code) == 0, gnis_to_code

    return {
        **osm,
        'cli': sys.argv,
        'elements': out_els,
    }


if __name__ == '__main__':
    osm_file, peaks_file = sys.argv[1:]
    output = run(osm_file, peaks_file)
    json.dump(output, sys.stdout, indent=2)
