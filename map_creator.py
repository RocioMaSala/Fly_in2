from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ZoneTypeError(Exception):
    def __init__(
            self, line_num: int, message: str = "Incorrect Zone Type"
            ) -> None:
        super().__init__(f"Line {line_num}, {message}")


class CapacityError(Exception):
    def __init__(
            self, line_num: int, message: str = "Invalid capacity"
            ) -> None:
        super().__init__(f"Line {line_num}, {message}")


class ZoneTypes(Enum):
    NORMAL = "normal"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
    BLOCKED = "blocked"


@dataclass
class Zone:
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
    zone_start: str
    zone_finish: str
    max_capacity: int = 1


@dataclass
class DroneMap:
    drone_number: int
    zone_map: dict[str, Zone] = field(default_factory=dict)
    connection_map: list[Connection] = field(default_factory=list)

    def adjacency(self) -> dict[str, list[str]]:
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
        capacity_map = {}
        for connection in self.connection_map:
            key = frozenset({connection.zone_start, connection.zone_finish})
            capacity_map[key] = connection.max_capacity
        return capacity_map


def parse_zone(line: str, line_num: int) -> Zone:
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
