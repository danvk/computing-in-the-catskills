import itertools
from typing import Dict, Iterable, List, Literal, TypedDict, Union


class OsmElementBase(TypedDict):
    id: int
    tags: Dict[str, any]


class OsmNode(OsmElementBase):
    type: Literal['node']
    lat: float
    lon: float


class OsmWay(OsmElementBase):
    type: Literal['way']
    nodes: List[int]


class RelationMember(TypedDict):
    type: Union[Literal['way'], Literal['node'], Literal['relation']]
    ref: int
    role: str


class OsmRelation(OsmElementBase):
    type: Literal['relation']
    members: List[RelationMember]


OsmElement = Union[OsmNode, OsmWay, OsmRelation]


def dedupe_ways(ways_with_dupes: Iterable[OsmWay]):
    """De-dupe a list of ways, preferring the version with more tags."""
    for _id, ways in itertools.groupby(
        sorted(
            ways_with_dupes,
            key=lambda way: (way['id'], -len(way.get('tags', [])))
        ),
        lambda way: way['id']
    ):
        yield next(ways)


def find_path(way: OsmWay, a: int, b: int) -> List[int]:
    """Find the subsequence of nodes between a and b, raising if there is none."""
    nodes = way['nodes']
    i = nodes.index(a)
    j = nodes.index(b)
    if i < j:
        return nodes[i:j+1]
    if j == 0:
        return nodes[i::-1]
    return nodes[i:j-1:-1]


CATSKILLS_BBOX = (41.813,-74.652,42.352,-73.862)


def is_in_catskills(lon: float, lat: float) -> bool:
    lat1, lon1, lat2, lon2 = CATSKILLS_BBOX
    return lat1 <= lat <= lat2 and lon1 <= lon <= lon2
