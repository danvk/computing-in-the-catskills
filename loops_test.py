import json

from loops import load_and_index, plausible_peak_sequences


G, peaks_to_lots = load_and_index(
    json.load(open('data/network+parking.geojson'))['features']
)


def test_zero_sequence():
    assert plausible_peak_sequences(G, []) == [(0, tuple())]


def test_one_sequence():
    # Individual peaks are always a valid sequence and have distance zero.
    # (or you can choose not to visit the peak)
    assert plausible_peak_sequences(G, [357574030]) == [(0, tuple()), (0, (357574030,))]


def test_two_sequence():
    # A pair of peaks (Sherrill and North Dome) can be traversed in either order,
    # or you can visit neither of them.
    assert sorted(plausible_peak_sequences(G, [10010091368, 357574030])) == [
        (0, tuple()),
        (0, (357574030,)),
        (0, (10010091368,)),
        (2.1774095560231563, (357574030, 10010091368)),
        (2.1774095560231563, (10010091368, 357574030)),
    ]


def test_two_sequence_inefficient():
    # You can't go between these two peaks (Sherrill and Westkill) without
    # crossing a third (North Dome).
    assert sorted(plausible_peak_sequences(G, [10010091368, 2955311547])) == [
        (0, tuple()),
        (0, (2955311547,)),
        (0, (10010091368,)),
    ]


def test_three_sequence():
    sherrill = 10010091368
    westkill = 2955311547
    northdome = 357574030
    assert sorted(plausible_peak_sequences(G, [sherrill, northdome, westkill])) == [
        (0, ()),
        (0, (357574030,)),
        (0, (2955311547,)),
        (0, (10010091368,)),
        (2.1774095560231563, (357574030, 10010091368)),
        (2.1774095560231563, (10010091368, 357574030)),
        (6.668030762071487, (357574030, 2955311547)),
        (6.668030762071487, (2955311547, 357574030)),
        # These two make sense
        (8.845440318094642, (2955311547, 357574030, 10010091368)),  # WK->ND->S
        (8.845440318094642, (10010091368, 357574030, 2955311547)),  # S->ND->WK
        # These four are more debatable
        (11.0228498741178, (357574030, 10010091368, 2955311547)),  # ND->S->WK
        (11.0228498741178, (2955311547, 10010091368, 357574030)),  # WK->S->ND
        (15.513471080166129, (357574030, 2955311547, 10010091368)),  # ND->WK->S
        (15.513471080166129, (10010091368, 2955311547, 357574030)),  # ND->WK->S
    ]


def test_six_sequence():
    # There are multiple sequences of the Spruceton Six that could be
    # optimal when connected to a parking lot to form a complete hike.
    pass
