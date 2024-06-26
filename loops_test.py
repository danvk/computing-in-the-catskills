import json

import json5

from loops import load_and_index, index_peaks, plausible_peak_sequences
from spec import Spec


spec = Spec(json5.load(open('data/catskills/spec.json5')))
features = json.load(open('data/catskills/network+parking.geojson'))['features']
G, peaks_to_lots = load_and_index(spec, features)

code_to_id = {
    f['properties']['code']: f['properties']['id']
    for f in features
    if 'code' in f['properties']
}
id_to_code = {v: k for k, v in code_to_id.items()}


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
    assert len(all_seqs) == 269
    # 177 sequences
    mega_spruceton = [
        (d, seq)
        for d, seq in all_seqs
        if len(seq) == 6 and seq[0] == sherrill and seq[-1] == rusk
    ]
    assert mega_spruceton == [
        (26.16, (sherrill, northdome, westkill, sw_hunter, hunter, rusk))
    ]

    from_sw_hunter = [
        (d, seq) for d, seq in all_seqs if len(seq) == 6 and seq[0] == sw_hunter
    ]
    # print(round_dseq(from_sw_hunter))
    assert from_sw_hunter == [
        (
            25.89,
            (1938215682, 1938201532, 10033501291, 2955311547, 357574030, 10010091368),
            # SW         H           R            W           ND         S
            # Visualize with:
            # poetry run python hike_sample.py --seq 1938215682,...,10010091368 \
            # data/catskills/network+parking.geojson data/catskills/hikes+ele.json \
            # | pbcopy
        ),
        (
            31.92,
            (1938215682, 1938201532, 10033501291, 357574030, 10010091368, 2955311547),
            # SW         H           R            ND         S            W
        ),
        (
            35.74,
            (1938215682, 2955311547, 10010091368, 357574030, 10033501291, 1938201532),
        ),
        (
            35.96,
            (1938215682, 1938201532, 2955311547, 357574030, 10010091368, 10033501291),
        ),
    ]


the_ten_codes = (
    'L',  # Lone
    'Ro',  # Rocky
    'Pk',  # Peekamoose
    'S',  # Slide
    'C',  # Cornell
    'W',  # Witt
    'Ta',  # Table
    'P',  # Panther
    'Fr',  # Friday
    'BC',  # Balsam Cap
)
the_ten = tuple(
    next(f['properties']['id'] for f in features if f['properties'].get('code') == code)
    for code in the_ten_codes
)


def test_ten_sequence():
    all_seqs = call_plausible_peak_sequences(G, the_ten)
    assert len(all_seqs) == 2221


def test_ten_sequence_max_depth():
    six_seqs = call_plausible_peak_sequences(G, the_ten, max_length=6)
    assert len(six_seqs) < 2221
    for _d, seq in six_seqs:
        assert len(seq) <= 6
    assert any(len(seq) == 6 for _d, seq in six_seqs)


the_nine_codes = (
    'L',  # Lone
    'Ro',  # Rocky
    'Pk',  # Peekamoose = 2398015279
    'S',  # Slide = 2426171552
    'C',  # Cornell
    'W',  # Witt
    'Ta',  # Table
    'Fr',  # Friday
    'BC',  # Balsam Cap
)
the_nine = tuple(code_to_id[code] for code in the_nine_codes)


def test_nine_sequence():
    all_seqs = call_plausible_peak_sequences(G, the_nine)
    # print(all_seqs[-1])
    all_nine = [(d, s) for (d, s) in all_seqs if len(s) >= 9]

    # print(code_to_id['Pk'])
    # print(code_to_id['S'])
    # print(all_seqs[:10])

    pk_to_s = [
        (d, s)
        for (d, s) in all_nine
        if s[0] == code_to_id['Pk'] and s[-1] == code_to_id['S']
    ]
    # print([id_to_code[id] for id in pk_to_s[0][1]])
    # print(peaks_to_lots)

    assert len(pk_to_s) == 1
