import itertools
from typing import Dict, Iterable, List, Literal, Tuple, TypedDict, Union
from util import catskills_haversine

from rich.console import Console

from util import haversine


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
        sorted(ways_with_dupes, key=lambda way: (way['id'], -len(way.get('tags', [])))),
        lambda way: way['id'],
    ):
        yield next(ways)


def find_path(way: OsmWay, a: int, b: int) -> List[int]:
    """Find the subsequence of nodes between a and b, raising if there is none."""
    nodes = way['nodes']
    ais = [i for i, v in enumerate(nodes) if v == a]
    bis = [i for i, v in enumerate(nodes) if v == b]
    assert ais and bis
    if len(ais) == 1 and len(bis) == 1:
        i = ais[0]
        j = bis[0]
    elif len(ais) == 2 and len(bis) == 1:
        j = bis[0]
        if abs(ais[0] - j) < abs(ais[1] - j):
            i = ais[0]
        else:
            i = ais[1]
    elif len(ais) == 1 and len(bis) == 2:
        i = ais[0]
        if abs(bis[0] - i) < abs(bis[1] - i):
            j = bis[0]
        else:
            j = bis[1]
    elif len(ais) == 2 and a == b:
        i = ais[0]
        j = ais[1]
    else:
        raise ValueError(f'Too complicated! {way["id"]} / {a} / {b}')
    if i < j:
        return nodes[i : j + 1]
    if j == 0:
        return nodes[i::-1]
    return nodes[i : j - 1 : -1]


def closest_point_on_trail(
    lon_lat: Tuple[float, float],
    trail_ways: List[OsmWay],
    trail_nodes: Dict[int, OsmNode],
):
    best_node = None
    best_d = 1000
    lon1, lat1 = lon_lat

    for way in trail_ways:
        for node_id in way['nodes']:
            node = trail_nodes[node_id]
            lon2 = node['lon']
            lat2 = node['lat']
            d = catskills_haversine(lon1, lat1, lon2, lat2)
            if d < best_d:
                best_d = d
                best_node = node
    return best_d * 1000, best_node


def distance(
    lon_lat: Tuple[float, float], element: OsmElement, nodes: Dict[int, OsmNode]
) -> float:
    lon1, lat1 = lon_lat

    if element['type'] == 'node':
        return 1000 * haversine(lon1, lat1, element['lon'], element['lat'])

    elif element['type'] == 'relation':
        raise NotImplementedError()

    best_d = 1000  # km
    for node_id in element['nodes']:
        node = nodes[node_id]
        lon2 = node['lon']
        lat2 = node['lat']
        d = haversine(lon1, lat1, lon2, lat2)
        if d < best_d:
            best_d = d
    return best_d * 1000


def element_centroid(el: OsmElement, nodes: Dict[int, OsmNode]) -> tuple[float, float]:
    if el['type'] == 'node':
        return el['lon'], el['lat']
    elif el['type'] == 'way':
        ns = el['nodes']
        return (
            sum(nodes[n]['lon'] for n in ns) / len(ns),
            sum(nodes[n]['lat'] for n in ns) / len(ns),
        )


def way_length(nodes: list[int], id_to_node: Dict[int, OsmNode]) -> float:
    node_els = [id_to_node[n] for n in nodes]
    return sum(
        haversine(a['lon'], a['lat'], b['lon'], b['lat'])
        for a, b in zip(node_els[:-1], node_els[1:])
    )


CATSKILLS_BBOX = (41.813, -74.855, 42.352, -73.862)


def is_in_catskills(lon: float, lat: float) -> bool:
    lat1, lon1, lat2, lon2 = CATSKILLS_BBOX
    return lat1 <= lat <= lat2 and lon1 <= lon <= lon2


def link(url: str, text: str):
    console = Console()
    with console.capture() as capture:
        console.print(f'[link={url}]{text}[/link]', end='')
    return capture.get()


def node_link(node: int, name: str | None = None):
    return link(
        f'https://www.openstreetmap.org/node/{node}',
        f'node/{node}' + (f' ({name})' if name else ''),
    )


def way_link(way: int, name: str | None = None):
    return link(
        f'https://www.openstreetmap.org/way/{way}',
        f'way/{way}' + (f' ({name})' if name else ''),
    )


def element_link(el: OsmElement):
    if el['type'] == 'node':
        return node_link(el['id'], el.get('tags', {}).get('name'))
    elif el['type'] == 'way':
        return way_link(el['id'], el.get('tags', {}).get('name'))
    raise NotImplementedError('Links to relations are not implemented.')


PEAKS = [
    ('S', 2426171552, 'Slide Mountain'),
    ('H', 1938201532, 'Hunter Mountain'),
    ('BD', 2473476912, 'Blackdome Mountain'),
    ('BH', 2473476747, 'Blackhead Mountain'),
    ('TC', 2473476927, 'Thomas Cole Mountain'),
    ('We', 2955311547, 'West Kill Mountain'),
    ('C', 2884119551, 'Cornell Mountain'),
    ('Ta', 7292479776, 'Table Mountain'),
    ('Pk', 2398015279, 'Peekamoose Mountain'),
    ('Pl', 2882649917, 'Plateau Mountain'),
    ('Su', 2882649730, 'Sugarloaf Mountain'),
    ('W', 2884119672, 'Wittenberg Mountain'),
    ('SW', 1938215682, 'Southwest Hunter'),
    ('L', -6601, 'Lone Mountain'),
    ('BL', 2897919022, 'Balsam Lake Mountain'),
    ('P', 9147145385, 'Panther Mountain'),
    ('BI', 357548762, 'Big Indian Mtn Mountain'),
    ('Fr', 9953707705, 'Friday Mountain'),
    ('Ru', 10033501291, 'Rusk Mountain'),
    ('KHP', 9785950126, 'Kaaterskill High Peak'),
    ('Tw', 7982977638, 'Twin Mountain'),
    ('BC', 9953729846, 'Balsam Cap Mountain'),
    ('Fi', 357559622, 'Fir Mountain'),
    ('ND', 357574030, 'North Dome Mountain'),
    ('B', 2845338212, 'Balsam Mountain'),
    ('Bp', 212348771, 'Bearpen Mountain'),
    ('E', 357557378, 'Eagle Mountain'),
    ('IH', 7978185605, 'Indian Head Mountain'),
    ('Sh', 10010091368, 'Sherrill Mountain'),
    ('V', -5149, 'Vly Mountain'),
    ('WHP', 2426236522, 'Windham High Peak'),
    ('Ha', 357563196, 'Halcott Mountain'),
    ('Ro', -6003, 'Rocky Mountain'),
]
