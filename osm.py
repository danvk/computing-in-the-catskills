from typing import Dict, List, Literal, TypedDict, Union


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
