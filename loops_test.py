import json

from loops import load_and_index, index_peaks, plausible_peak_sequences


G, peaks_to_lots = load_and_index(
    json.load(open('data/network+parking.geojson'))['features']
)


def round_dseq(dseq):
    return [(round(d, 2), seq) for d, seq in dseq]


def call_plausible_peak_sequences(G, peaks, max_length=None):
    peak_idx = index_peaks(G, peaks)
    seqs = [
        *sorted(
            round_dseq(
                plausible_peak_sequences(
                    G, peaks, peak_idx, max_length=(max_length or 100)
                )
            )
        )
    ]
    return seqs


def test_zero_sequence():
    assert plausible_peak_sequences(G, [], {}) == [(0, tuple())]


def test_one_sequence():
    # Individual peaks are always a valid sequence and have distance zero.
    # (or you can choose not to visit the peak)
    assert plausible_peak_sequences(G, [357574030], {}) == [
        (0, tuple()),
        (0, (357574030,)),
    ]


def test_two_sequence():
    # A pair of peaks (Sherrill and North Dome) can be traversed in either order,
    # or you can visit neither of them.
    assert call_plausible_peak_sequences(G, [10010091368, 357574030]) == [
        (0, tuple()),
        (0, (357574030,)),
        (0, (10010091368,)),
        (2.18, (357574030, 10010091368)),
        (2.18, (10010091368, 357574030)),
    ]


def test_two_sequence_inefficient():
    # You can't go between these two peaks (Sherrill and Westkill) without
    # crossing a third (North Dome).
    assert call_plausible_peak_sequences(G, [10010091368, 2955311547]) == [
        (0, tuple()),
        (0, (2955311547,)),
        (0, (10010091368,)),
    ]


def test_three_sequence():
    sherrill = 10010091368
    westkill = 2955311547
    northdome = 357574030
    assert call_plausible_peak_sequences(G, [sherrill, northdome, westkill]) == [
        (0, ()),
        (0, (357574030,)),
        (0, (2955311547,)),
        (0, (10010091368,)),
        (2.18, (357574030, 10010091368)),
        (2.18, (10010091368, 357574030)),
        (6.67, (357574030, 2955311547)),
        (6.67, (2955311547, 357574030)),
        # These two make sense
        (8.85, (2955311547, 357574030, 10010091368)),  # WK->ND->S
        (8.85, (10010091368, 357574030, 2955311547)),  # S->ND->WK
        # These four are more debatable
        (11.02, (357574030, 10010091368, 2955311547)),  # ND->S->WK
        (11.02, (2955311547, 10010091368, 357574030)),  # WK->S->ND
        (15.51, (357574030, 2955311547, 10010091368)),  # ND->WK->S
        (15.51, (10010091368, 2955311547, 357574030)),  # ND->WK->S
    ]


def test_six_sequence():
    # There are multiple sequences of the Spruceton Six that could be
    # optimal when connected to a parking lot to form a complete hike.
    sherrill = 10010091368
    westkill = 2955311547
    northdome = 357574030
    sw_hunter = 1938215682
    hunter = 1938201532
    rusk = 10033501291
    all_seqs = call_plausible_peak_sequences(
        G, [sherrill, northdome, westkill, sw_hunter, hunter, rusk]
    )
    assert len(all_seqs) == 123
    # 177 sequences
    mega_spruceton = [
        (d, seq)
        for d, seq in all_seqs
        if len(seq) == 6 and seq[0] == sherrill and seq[-1] == rusk
    ]
    assert mega_spruceton == [
        (26.14, (sherrill, northdome, westkill, sw_hunter, hunter, rusk))
    ]

    from_sw_hunter = [
        (d, seq) for d, seq in all_seqs if len(seq) == 6 and seq[0] == sw_hunter
    ]
    # print(round_dseq(from_sw_hunter))
    assert from_sw_hunter == [
        (
            33.22,
            (1938215682, 10033501291, 1938201532, 2955311547, 357574030, 10010091368),
        ),
        (
            40.46,
            (1938215682, 10010091368, 357574030, 2955311547, 1938201532, 10033501291),
        ),
    ]


the_ten = (
    -6003,
    -6601,
    2398015279,
    2426171552,
    2884119551,
    2884119672,
    7292479776,
    9147145385,
    9953707705,
    9953729846,
)


def test_ten_sequence():
    # 2821 / 9864101
    all_seqs = call_plausible_peak_sequences(G, the_ten)
    assert len(all_seqs) == 2821


def test_ten_sequence_max_depth():
    six_seqs = call_plausible_peak_sequences(G, the_ten, max_length=6)
    assert len(six_seqs) < 2821
    for _d, seq in six_seqs:
        assert len(seq) <= 6
    assert any(len(seq) == 6 for _d, seq in six_seqs)
