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


def parse_zone(line: str, line_num: int) -> Zone:
    """Parse a single zone dfinition line into a class 'Zone'.

    Handles the "start_hub", "end_hub", and "hub" line prefixes,
    the mandatory name and integer coordinates, and any optional
    [zone=..., color=..., max_drones=...] metadata block.

    Args:
        line: Raw line of text from the map file.
        line_num: 1-indexed line number, used for error reporting.

    Returns:
        The class 'Zone' described by the line.

    Raises:
        ValueError: If the zone name is invalid, the coordinates are
        missing or non-integer, or the metadata block is malformed.
        ZoneTypeError: If the "zone" metadata value is not a valid class
        'ZoneTypes' member.
    """
    parts = line.strip().split()
    hub_type = parts[0]
    start_zone = hub_type == "start_hub:"
    finish_zone = hub_type == "end_hub:"

    name = parts[1]
    if "-" in name:
        raise ValueError(
            f"Parsing Error: Zone name '{name}' "
            f"cannot contain dashes, line {line_num}"
            )

    if " " in name:
        raise ValueError(
            f"Parsing Error: Zone name '{name}' "
            f"cannot contain spaces, line {line_num}"
            )

    try:
        coord_x = int(parts[2])
        coord_y = int(parts[3])
    except (IndexError, ValueError):
        raise ValueError(
            f"Parsing Error: Invalid or missing integer coordinates, "
            f"line {line_num}"
            )

    zone_type = ZoneTypes.NORMAL
    color = None
    max_drones = 1

    if "[" in line:
        try:
            metadata_part = line.split("[")[1].split("]")[0].strip()
            metadata_pairs = metadata_part.split()
            metadata_dict = {
                k: v for k, v in (pair.split("=") for pair in metadata_pairs)
                }
            for k, v in metadata_dict.items():
                if k == "zone":
                    try:
                        zone_type = ZoneTypes(v)
                    except ValueError:
                        raise ZoneTypeError(line_num)
                if k == "color":
                    color = v
                if k == "max_drones":
                    max_drones = int(v)

        except ZoneTypeError:
            raise
        except Exception:
            raise ValueError(f"Parsing Error: Invalid metadata syntax, "
                             f"line {line_num}")

    return Zone(
        name=name,
        coord_x=coord_x,
        coord_y=coord_y,
        start_zone=start_zone,
        finish_zone=finish_zone,
        max_drones=max_drones,
        zone_type=zone_type,
        color=color,
        )


def parse_connection(line: str, line_num: int) -> Connection:
    """Parse a single connection definition line into a class 'Connection'.

    Handles the "connection: zone1-zone2 " syntax and the optional "[max_link_
    capacity=...] metadata block.

    Args:
        line: Raw line of the text from the map file.
        line_num: 1-indexed line number, used for error reporting.

    Returns:
        The class 'Connection' described by the line.

    Raises:
        ValueError: If the connection format is invalid, the two zone
        names are identical, or the metadata block is malformed.
        CapacityError: If 'max_link_capacity' is not a positive integer.
    """
    parts = line.strip().split()
    try:
        connection_part = parts[1]
        if "-" not in connection_part:
            raise ValueError
        zone_start, zone_finish = connection_part.split("-", 1)

    except (IndexError, ValueError):
        raise ValueError(f"Parsing Error: Invalid connection format, expected "
                         f"'zone1-zone2', line {line_num}")

    if zone_start == zone_finish:
        raise ValueError(
            f"Parsing Error: A zone cannot connect to itself, line {line_num}"
            )

    max_capacity = 1

    if "[" in line:
        try:
            content_inside = line.split("[")[1].split("]")[0].strip()

            if "=" not in content_inside:
                raise ValueError

            key, value = content_inside.split("=", 1)

            if key.strip() != "max_link_capacity":
                raise ValueError

            max_capacity = int(value.strip())

            if max_capacity <= 0:
                raise CapacityError(line_num)

        except CapacityError:
            raise

        except Exception:
            raise ValueError(
                f"Parsing Error: Invalid connection metadata "
                f"syntax, line {line_num}")

    return Connection(zone_start, zone_finish, max_capacity)
