import networkx as nx

from graph import get_lot_index, get_peak_index, read_hiking_graph
from util import orient


def geojson_for_hike(features, d_km, seq):
    G = read_hiking_graph(features)
    id_to_peak = get_peak_index(features)
    id_to_lot = get_lot_index(features)
    peak_features = [*id_to_peak.values()]
    id_to_feature = {
        f['properties']['id']: f for f in features if 'id' in f['properties']
    }

    fs = [f for f in peak_features if f['properties']['id'] in seq]
    for f in fs:
        f['properties']['marker-size'] = 'small'
    fs.append(id_to_lot[seq[0]])
    if seq[0] != seq[-1]:
        fs.append(id_to_lot[seq[-1]])
    coordinates = []
    for a, b in zip(seq[:-1], seq[1:]):
        path = nx.shortest_path(G, a, b, weight='weight')
        coordinates += [
            orient(
                G.edges[node_a, node_b]['feature']['geometry']['coordinates'],
                id_to_feature[node_a]['geometry']['coordinates'],
            )
            for node_a, node_b in zip(path[:-1], path[1:])
        ]
    hike_feature = {
        'type': 'Feature',
        'properties': {
            'nodes': seq,
            'd_km': round(d_km, 2),
            'd_mi': round(d_km * 0.621371, 2),
            'peaks': [id_to_peak[node]['properties']['name'] for node in seq[1:-1]],
        },
        'geometry': {'type': 'MultiLineString', 'coordinates': coordinates},
    }
    fs.append(hike_feature)
    return {'type': 'FeatureCollection', 'features': fs}


def gpx_for_hike(features, d_km, seq):
    fs = geojson_for_hike(features, d_km, seq)
    return geojson_to_gpx(fs['features'][-1])


def get_coordinates(geom):
    if geom['type'] == 'Point':
        return [geom['coordinates']]
    elif geom['type'] == 'LineString':
        return geom['coordinates']
    elif geom['type'] == 'MultiLineString':
        return [coord for ls in geom['coordinates'] for coord in ls]
    raise ValueError(f'Unknown geometry {geom["type"]}')


def geojson_to_gpx(feature):
    trk_pts = '\n'.join(
        f'<trkpt lat="{lat}" lon="{lng}"></trkpt>'
        for lng, lat in get_coordinates(feature['geometry'])
    )
    return f'''<?xml version="1.0"?>
  <gpx
    xmlns="http://www.topografix.com/GPX/1/1"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    version="1.1"
    xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
    <metadata>
      <name><![CDATA[Hike title]]></name>
      <desc><![CDATA[Hike description]]></desc>
    </metadata>
    <trk>
      <name><![CDATA[Hike Name]]></name>
      <src>DanVK's Catskills Hike Planner</src>
      <trkseg>
        {trk_pts}
      </trkseg>
    </trk>
  </gpx>
  '''
