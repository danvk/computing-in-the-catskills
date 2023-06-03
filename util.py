from math import radians, cos, sin, asin, sqrt
from typing import List, Tuple, TypeVar

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
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r


def pairkey(a: int, b: int) -> Tuple[int, int]:
    """Return the two ints as an ordered tuple."""
    return (a, b) if a <= b else (b, a)

T = TypeVar("T")

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
