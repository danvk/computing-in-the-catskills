import json

from loops import load_and_index, plausible_peak_sequences


G, peaks_to_lots = load_and_index(
    json.load(open('data/network+parking.geojson'))['features']
)


def test_one_sequence():
    # Individual peaks are always a valid sequence and have distance zero.
    assert plausible_peak_sequences(G, [357574030]) == [(0, (357574030,))]


def test_two_sequence():
    # A pair of peaks can be traversed in either order.
    assert sorted(plausible_peak_sequences(G, [10010091368, 357574030])) == [
        (0, (357574030,)),
        (0, (10010091368,)),
        (2.1774095560231563, (357574030, 10010091368)),
        (2.1774095560231563, (10010091368, 357574030)),
    ]


def test_six_sequence():
    # There are multiple sequences of the Spruceton Six that could be
    # optimal when connected to a parking lot to form a complete hike.
    pass
