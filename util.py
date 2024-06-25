import itertools
from math import radians, cos, sin, asin, sqrt
import math
import time
from typing import Iterable, List, Tuple, TypeVar, Callable


# https://stackoverflow.com/a/4913653/388951
def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers. Use 3956 for miles.
    # Determines return value units.
    r = 6371
    return c * r


m_per_lng = 82526.71005845172
m_per_lat = 111194.9266445589

MI_PER_KM = 0.621371


def catskills_haversine(lon1, lat1, lon2, lat2):
    """Much faster approximation to haversine() for the Catskills region."""
    return 0.001 * sqrt(
        ((lon2 - lon1) * m_per_lng) ** 2 + ((lat2 - lat1) * m_per_lat) ** 2
    )


def pairkey(a: int, b: int) -> Tuple[int, int]:
    """Return the two ints as an ordered tuple."""
    return (a, b) if a <= b else (b, a)


T = TypeVar("T")
U = TypeVar("U")


def splitlist(xs: List[T], delim: T) -> List[List[T]]:
    chunks = []
    last = 0
    for x in xs:
        if x == delim:
            last = delim
            continue

        if last == delim:
            chunks.append([x])
        else:
            chunks[-1].append(x)
        last = x
    return chunks


def rotate_to_start(xs: List[T], desired_first: T) -> List[T]:
    """Rotate a list so that it starts with a particular element."""
    i = xs.index(desired_first)
    return xs[i:] + xs[:i]


def powerfact(n):
    """Total number of permutations of all subsets of an n-set."""
    # https://oeis.org/A000522
    total = 0
    for i in range(0, n + 1):
        total += math.comb(n, i) * math.factorial(i)
    return total


def powerset(xs):
    return (
        combo for r in range(len(xs) + 1) for combo in itertools.combinations(xs, r)
    )


def index_by(xs: Iterable[T], key: Callable[[T], U]) -> dict[U, list[T]]:
    out: dict[U, list[T]] = {}
    for x in xs:
        k = key(x)
        out.setdefault(k, [])
        out[k].append(x)
    return out


def orient(coords: list[T], desired_first: T) -> list[T]:
    if coords[-1] == desired_first:
        return coords[::-1]
    return coords


class Timer:
    def __enter__(self):
        self.start_secs = time.time()
        return self

    def __exit__(self, type, value, traceback):
        elapsed_secs = time.time() - self.start_secs
        print(f'Elapsed time: {elapsed_secs:g}s')
