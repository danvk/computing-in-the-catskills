#!/usr/bin/env python

import sys
import json
from pathlib import Path
from typing import List
from collections import Counter

import requests


def fetch_from_overpass(query: str) -> str:
    r = requests.post('https://overpass-api.de/api/interpreter', data={'data': query})
    r.raise_for_status()
    return r.text


def element_stats(elements: List[any]):
    return Counter(e['type'] for e in elements)


for path in sys.argv[1:]:
    p = Path(path).name
    query = open(path).read()
    print(f'Running query {path}')
    result = fetch_from_overpass(query)
    with open(Path('data') / p.replace('.txt', '.json'), 'w') as out:
        out.write(result)
        stats = element_stats(json.loads(result)['elements'])
        rels = stats.get('relation') or 0
        ways = stats.get('way') or 0
        nodes = stats.get('node') or 0
        print(f'  -> {len(result)} bytes, rel={rels}, way={ways}, node={nodes}')
