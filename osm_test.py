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

    # With multiple paths between two nodes within a way, pick the shorter one.
    way_with_dupe_nodes = {
        'type': 'way',
        'id': 287207779,
        'nodes': [
            2908399218,
            1,
            2,
            3,
            4,
            5,
            6,
            2908399438,
            7,
            8,
            9,
            2908399218,
        ],
    }
    path = find_path(way_with_dupe_nodes, 2908399438, 2908399218)
    assert path == [2908399438, 7, 8, 9, 2908399218]

    way_with_dupe_nodes = {
        'type': 'way',
        'id': 287207779,
        'nodes': [
            2908399218,
            1,
            2,
            3,
            4,
            5,
            6,
            2908399438,
            7,
            8,
            9,
            2908399438,
        ],
    }
    path = find_path(way_with_dupe_nodes, 2908399438, 2908399438)
    assert path == [2908399438, 7, 8, 9, 2908399438]
