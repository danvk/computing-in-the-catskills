from osm import find_path


def test_find_path():
    way = {
        'type': 'way',
        'id': 155801023,
        'nodes': [7624362371, 213833732, 213833734, 10741871039],
    }
    path = find_path(way, 213833732, 7624362371)
    assert path == [213833732, 7624362371]

    path = find_path(way, 7624362371, 213833732)
    assert path == [7624362371, 213833732]

    path = find_path(way, 213833732, 10741871039)
    assert path == [213833732, 213833734, 10741871039]

    path = find_path(way, 10741871039, 213833732)
    assert path == [10741871039, 213833734, 213833732]
