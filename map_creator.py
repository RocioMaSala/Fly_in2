from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ZoneTypeError(Exception):
    """ Raised when a zone's ""zone"" metadata value is not a valid type.

    Args:
        line_num: line number in the source file where the error occurred.
        message: Human-readable description of the error.
    """
    def __init__(
            self, line_num: int, message: str = "Incorrect Zone Type"
            ) -> None:
        super().__init__(f"Line {line_num}, {message}")


class CapacityError(Exception):
    """Raised when a capacity value (zone or connection) is invalid.

    Args:
        line_num: Line number in the source file where the error occured.
        message: Human-readable description of the error.
    """
    def __init__(
            self, line_num: int, message: str = "Invalid capacity"
            ) -> None:
        super().__init__(f"Line {line_num}, {message}")


class ZoneTypes(Enum):
    """Valid zone types accepted by the map format.

    Attributes:
        NORMAL: Standard zone, costs 1 turn to enter.
        RESTRICTED: Sensitive zone, costs 2 turns to enter.
        PRIORITY: Preferred zone, costs 1 turn but should be favored by
        pathfinding.
        BLOCKED: Inaccessible zone; drones may not enter it.
    """

    NORMAL = "normal"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
    BLOCKED = "blocked"


@dataclass
class Zone:
    """ A single zone (node) in the drone network.

    Attributes:
        name: Unique identifier of the zone.
        coord_x: Integer x coordinate of the zone.
        coord_y: Integer y coordinate of the zone.
        start_zone: Whether this zone is the unique starting hub.
        end_zone: Whether this zone is the unique ending hub.
        max_drones: Maximum number of drones the zone can hold at once.
        zone_type: The zone's type, affecting movement cost and access.
        color: Optional color tag used for visual representation.

    """

    name: str
    coord_x: int
    coord_y: int
    start_zone: bool = False
    finish_zone: bool = False
    max_drones: int = 1
    zone_type: ZoneTypes = ZoneTypes.NORMAL
    color: Optional[str] = None


@dataclass
class Connection:
    """ A bidirectional edge between two zones.

    Attributes:
        zone_start: Name of one of the two connected zones.
        zone_finish: Name of the other connected zone.
        max_capacity: Maximum number of drones that may traverse this
        connection simultaneously.
    """

    zone_start: str
    zone_finish: str
    max_capacity: int = 1


@dataclass
class DroneMap:
    """The full parsed representation of a drone network map.

    Attributes:
        drone_number: Number of drones to route through the network.
        zone_map: Mapping of zone name to its class 'Zone' instance.
        connection_map: List of all class 'Connection' instances in the
        network.

    """

    drone_number: int
    zone_map: dict[str, Zone] = field(default_factory=dict)
    connection_map: list[Connection] = field(default_factory=list)

    def adjacency(self) -> dict[str, list[str]]:
        """Build an adjacency list from the map's connections.

        Returns:
            A dict mapping each zone name to the list of zone names it
            is directly connected to (connections are treated as bidirectional)
            .
        """
        dict_adjacency: dict[str, list[str]] = {}
        for conection in self.connection_map:
            if conection.zone_start not in dict_adjacency:
                dict_adjacency[conection.zone_start] = []
            dict_adjacency[conection.zone_start].append(conection.zone_finish)
            if conection.zone_finish not in dict_adjacency:
                dict_adjacency[conection.zone_finish] = []
            dict_adjacency[conection.zone_finish].append(conection.zone_start)
        return dict_adjacency

    def link_capacity(self) -> dict[frozenset[str], int]:
        """Build a lookup of maximum capacity per connection.

        Returns:
            A dict mapping each connection, represented as a ''frozenset' of
            its two zone names, to its 'max_capacity'.
        """
        capacity_map = {}
        for connection in self.connection_map:
            key = frozenset({connection.zone_start, connection.zone_finish})
            capacity_map[key] = connection.max_capacity
        return capacity_map
