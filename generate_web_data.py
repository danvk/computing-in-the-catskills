"""Generate JSON, TS, or GeoJSON formatted data for the web app."""

import json
import sys


if __name__ == '__main__':
    geojson_file, output_format = sys.argv[1:]
    assert output_format in ('ts', 'py', 'geojson')
    features = json.load(open(geojson_file))['features']

    peaks = [
        (f['properties']['code'], f['properties']['id'], f['properties']['name'])
        for f in features
        if f['properties'].get('type') == 'high-peak'
    ]

    if output_format == 'py':
        print('PEAKS = ', end='')
        json.dump(peaks, sys.stdout, indent=2)

    elif output_format == 'ts':
        code_to_name = {code: name for code, _id, name in peaks}
        print('export const PEAKS = ', end='')
        json.dump(code_to_name, sys.stdout, indent=2)

    else:
        features = [
            {
                "type": "Feature",
                'geometry': f['geometry'],
                "properties": {
                    **f['properties'],
                    "type": "dec",
                    # Matches HikePlanner.tsx
                    "name": f['properties']['name']
                    .replace(' Mountain', '')
                    .replace('Mount ', '')
                    .replace(' Peak', ''),
                },
            }
            for f in features
            if f['properties'].get('type') == 'high-peak'
        ]
        json.dump(
            {'type': 'FeatureCollection', 'features': features}, sys.stdout, indent=2
        )
