import sys
from map_creator import DroneMap, parse_zone, parse_connection


class UsageError(Exception):
    """Raised when the script is invoked with the wrong command-line usage.

    Args:
        message: Human-readable description of the error.
    """
    def __init__(self, message: str = "Usage Error: make run MAP='XXXXXX'"
                 ) -> None:
        super().__init__(message)


class MissingDroneNumber(Exception):
    """ Raised when the map file does not declare a drone number at all.

    Args:
        message: Human-readable description of the error.
    """

    def __init__(
            self, message: str = "Index Error: A drone number is needed"
            ) -> None:
        super().__init__(message)


class DroneNumberError(Exception):
    """Raised when the declared drone number is missing, malformed or out
    of the accepted range.

    Args:
        message: Human-readable description of the error.
    """

    def __init__(
            self, message: str = "Value Error: A valid drone number is needed"
            ) -> None:
        super().__init__(message)


def map_creation() -> tuple[DroneMap, bool]:
    """Parse the map file given on the command line into a 'DroneMap'.

    Reads the path from 'sys.argv', validates the 'nb_drones' header, then
    parses every zone and connection line into the returned 'DroneMap',
    enforcing the suject's parser constraints: exactly one 'start_hub' and
    one 'end_hub', no duplicate coordinates, no duplicate connections, and
    drone count within the start/end hub capacities. The optional
    '--capacity-info' flag is also read from the command line.

    Returns:
        A tuple of the fully populated 'DroneMap' and a boolean flag indicating
        whether '--capacity-info' was passed on the command line.

    Raises:
        UsageError: If the command line does not contain exactly one
            positional argument (the map file path).
        MissingDroneNumber: If the file has no 'nb_drones' line
            before any other content.
        DroneNumberError: If the drone number is missing, not a valid
            integer, not positive, or exceeds the allowed maximum.
        ValueError: For any other parsing error - duplicate zone
            coordinates, multiple or missing 'start_hub'/'end_hub',
            connections referencing undefined zones, duplicate
            connections, or a drone count exceeding hub capacity.
        FileNotFoundError: If the given map file path does not exist.
        """
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    capacity_info = "--capacity-info" in sys.argv
    if len(args) != 1:
        raise UsageError
    try:
        with open(args[0]) as file:
            line_num = 0
            drone_nbr = None
            start_hub_name = None
            end_hub_name = None
            for line in file:
                line_num += 1
                line_clean = line.strip()

                if not line_clean or line_clean.startswith("#"):
                    continue

                if not line_clean.startswith("nb_drones:"):
                    raise DroneNumberError(
                        "Value Error: Expected 'nb_drones:', "
                        f"line {line_num}")

                try:
                    value_part = line_clean.split(":", 1)[1].strip()
                    drone_nbr = int(value_part)
                    if drone_nbr > 301:
                        raise DroneNumberError(
                            "Value Error: Drone Number must be less than 50"
                        )
                except (IndexError, ValueError):
                    raise DroneNumberError(
                        "Value Error: A valid drone number is "
                        f"needed, line {line_num}")

                if drone_nbr <= 0:
                    raise DroneNumberError(
                        "Value Error: Drone number must be a "
                        f"positive integer, line {line_num}")
                break

            if drone_nbr is None:
                raise MissingDroneNumber(
                    "Index Error: A drone number is "
                    "needed at the beginning of the file"
                    )

            map = DroneMap(drone_nbr)

            seen_coords = set()
            for line in file:
                line_num += 1
                line_clean = line.strip()
                if not line_clean or line_clean.startswith("#"):
                    continue
                if line_clean.startswith(("start_hub", "end_hub", "hub")):
                    zone = parse_zone(line, line_num)
                    actual_coords = (zone.coord_x, zone.coord_y)
                    if actual_coords in seen_coords:
                        raise ValueError(
                            "Parsing Error: Coordinates duplicated "
                            f"for '{zone.name}', "
                            f"line {line_num}"
                        )
                    seen_coords.add(actual_coords)
                    if line_clean.startswith("start_hub:"):
                        if start_hub_name is not None:
                            raise ValueError(
                                f"Parsing Error: Multiple strt_hubs detected, "
                                f"line {line_num}")
                        start_hub_name = zone.name
                        if "max_drones" not in line_clean:
                            zone.max_drones = drone_nbr
                        max_cpacity_strt = zone.max_drones

                    elif line_clean.startswith("end_hub:"):
                        if end_hub_name is not None:
                            raise ValueError(
                                f"Parsing Error: Multiple end_hubs detected, "
                                f"line {line_num}")
                        end_hub_name = zone.name
                        if "max_drones" not in line_clean:
                            zone.max_drones = drone_nbr
                        max_cpacty_finish = zone.max_drones

                    map.zone_map[zone.name] = zone

                elif line.strip().startswith("connection"):
                    connection = parse_connection(line, line_num)

                    if connection.zone_start not in map.zone_map:
                        raise ValueError(
                            f"Parsing Error: Zone '{connection.zone_start}' "
                            f"is not defined, line {line_num}")
                    if connection.zone_finish not in map.zone_map:
                        raise ValueError(
                            f"Parsing Error: Zone '{connection.zone_finish}' "
                            f"is not defined, line {line_num}")
                    for existing_conn in map.connection_map:
                        ex_start = existing_conn.zone_start
                        ex_finish = existing_conn.zone_finish
                        c_start = connection.zone_start
                        c_finish = connection.zone_finish

                        match_direct = (
                            ex_start == c_start and ex_finish == c_finish
                        )
                        match_inverted = (
                            ex_start == c_finish and ex_finish == c_start
                        )

                        if match_direct or match_inverted:
                            raise ValueError(
                                "Parsing Error: Duplicate connection between "
                                f"'{connection.zone_start}' "
                                f"and '{connection.zone_finish}', "
                                f"line {line_num}")
                    map.connection_map.append(connection)

            if start_hub_name is None:
                raise ValueError(
                    "Parsing Error: Missing 'start_hub:' zone in the file"
                    )

            if end_hub_name is None:
                raise ValueError(
                    "Parsing Error: Missing 'end_hub:' zone in the file"
                    )

            if start_hub_name == end_hub_name:
                raise ValueError(
                    "Parsing Error: 'start_hub' and 'end_hub' "
                    f"cannot be the same ('{start_hub_name}')")

            if drone_nbr > max_cpacty_finish and drone_nbr > max_cpacity_strt:
                raise ValueError(
                    "Parsing Error: Drone number is greater "
                    "than start_hub and finish_hub capacity"
                    )

            elif drone_nbr > max_cpacty_finish:
                raise ValueError(
                    "Parsing Error: Drone number is greater "
                    "than finish_hub capacity"
                    )

            elif drone_nbr > max_cpacity_strt:
                raise ValueError(
                    "Parsing Error: Drone number is greater "
                    "than start_hub capacity"
                    )

        return map, capacity_info
    except FileNotFoundError:
        raise FileNotFoundError("File not present")
