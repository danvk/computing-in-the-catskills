#!/usr/bin/env python

import sys
from pathlib import Path

import requests


def fetch_from_overpass(query: str) -> str:
    r = requests.post(f'https://overpass-api.de/api/interpreter', data={'data': query})
    r.raise_for_status()
    return r.text


for path in sys.argv[1:]:
    p = Path(path).name
    query = open(path).read()
    print(f'Running query {path}')
    result = fetch_from_overpass(query)
    with open(Path('data') / p.replace('.txt', '.json'), 'w') as out:
        print(f'Got {len(result)} bytes back')
        out.write(result)
