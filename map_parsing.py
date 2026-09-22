import sys
from map_creator import DroneMap, parse_zone, parse_connection
from typing import TextIO


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


class MapParser:
    """Parses a map definition file into a `DroneMap`.

    Encapsulates all the state needed while parsing (the current line
    number, the coordinates already seen, the start/end hub names found so
    far, and their capacities) as instance attributes instead of loose
    local variables, so each parsing step can be a small, testable method
    operating on `self`.

    Attributes:
        file_path: Path to the map file to parse.
        capacity_info: Whether the ``--capacity-info`` flag was passed on
            the command line.
        line_num: 1-indexed number of the last line read, used for error
            reporting.
        drone_nbr: The number of drones declared in the file, once parsed.
        drone_map: The `DroneMap` being built, once the drone count is
            known.
        start_hub_name: Name of the `start_hub` zone found so far, or
            `None` if not yet found.
        end_hub_name: Name of the `end_hub` zone found so far, or `None`
            if not yet found.
        seen_coords: Coordinates already used by a previously parsed zone,
            to detect duplicates.
        max_capacity_start: The `start_hub` zone's `max_drones` value.
        max_capacity_finish: The `end_hub` zone's `max_drones` value.
    """

    MAX_DRONES = 301

    def __init__(self, file_path: str, capacity_info: bool = False) -> None:
        self.file_path = file_path
        self.capacity_info = capacity_info
        self.line_num = 0
        self.drone_nbr: int
        self.drone_map: DroneMap
        self.start_hub_name: str | None = None
        self.end_hub_name: str | None = None
        self.seen_coords: set[tuple[int, int]] = set()
        self.max_capacity_start: int
        self.max_capacity_finish: int

    @classmethod
    def from_argv(cls) -> "MapParser":
        """Build a `MapParser` from the process's command-line arguments.

        Returns:
            A `MapParser` configured with the map file path and
            `--capacity-info` flag read from `sys.argv`.

        Raises:
            UsageError: If the command line does not contain exactly one
                positional argument (the map file path).
        """
        args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
        capacity_info = "--capacity-info" in sys.argv
        if len(args) != 1:
            raise UsageError
        return cls(args[0], capacity_info)

    def parse(self) -> tuple[DroneMap, bool]:
        """Parse the configured map file into a `DroneMap`.

        Returns:
            A tuple of the fully populated `DroneMap` and the
            `capacity_info` flag.

        Raises:
            MissingDroneNumber: If the file has no ``nb_drones:`` line
                before any other content.
            DroneNumberError: If the drone number is missing, not a
                valid integer, not positive, or exceeds the allowed
                maximum.
            ValueError: For any other parsing error — duplicate zone
                coordinates, multiple or missing `start_hub`/`end_hub`,
                connections referencing undefined zones, duplicate
                connections, or a drone count exceeding hub capacity.
            FileNotFoundError: If the given map file path does not exist.
        """
        try:
            with open(self.file_path) as file:
                self._parse_drone_count(file)
                self.drone_map = DroneMap(self.drone_nbr)
                self._parse_body(file)
                self._validate_hubs()
        except FileNotFoundError:
            raise FileNotFoundError("File not present")

        return self.drone_map, self.capacity_info

    def _parse_drone_count(self, file: TextIO) -> None:
        """Read and validate the mandatory leading ``nb_drones:`` line.

        Args:
            file: The open map file, positioned at its first line.

        Raises:
            DroneNumberError: If the first non-comment line is missing,
                malformed, or not a valid positive drone count within
                range.
            MissingDroneNumber: If the file has no content at all before
                EOF.
        """
        for line in file:
            self.line_num += 1
            line_clean = line.strip()

            if not line_clean or line_clean.startswith("#"):
                continue

            if not line_clean.startswith("nb_drones:"):
                raise DroneNumberError(
                    "Value Error: Expected 'nb_drones:', "
                    f"line {self.line_num}")

            try:
                value_part = line_clean.split(":", 1)[1].strip()
                drone_nbr = int(value_part)
                if drone_nbr > self.MAX_DRONES:
                    raise DroneNumberError(
                        "Value Error: Drone Number must be less than 50"
                    )
            except (IndexError, ValueError):
                raise DroneNumberError(
                    "Value Error: A valid drone number is "
                    f"needed, line {self.line_num}")

            if drone_nbr <= 0:
                raise DroneNumberError(
                    "Value Error: Drone number must be a "
                    f"positive integer, line {self.line_num}")

            self.drone_nbr = drone_nbr
            break

        if self.drone_nbr is None:
            raise MissingDroneNumber(
                "Index Error: A drone number is "
                "needed at the beginning of the file"
                )

    def _parse_body(self, file: TextIO) -> None:
        """Parse every remaining zone and connection line in the file.

        Args:
            file: The open map file, positioned right after the
                ``nb_drones:`` line.
        """
        for line in file:
            self.line_num += 1
            line_clean = line.strip()
            if not line_clean or line_clean.startswith("#"):
                continue
            if line_clean.startswith(("start_hub", "end_hub", "hub")):
                self._handle_zone_line(line, line_clean)
            elif line_clean.startswith("connection"):
                self._handle_connection_line(line)

    def _handle_zone_line(self, line: str, line_clean: str) -> None:
        """Parse one zone line and register it on `drone_map`.

        Also tracks duplicate coordinates and records the start/end hub
        name and capacity when the line defines one of them.

        Args:
            line: Raw line of text from the map file.
            line_clean: The same line, stripped of surrounding whitespace.

        Raises:
            ValueError: If the zone's coordinates duplicate a
                previously seen zone, or if a second `start_hub` or
                `end_hub` is found.
        """
        zone = parse_zone(line, self.line_num)
        actual_coords = (zone.coord_x, zone.coord_y)
        if actual_coords in self.seen_coords:
            raise ValueError(
                "Parsing Error: Coordinates duplicated "
                f"for '{zone.name}', "
                f"line {self.line_num}"
            )
        self.seen_coords.add(actual_coords)

        if line_clean.startswith("start_hub:"):
            if self.start_hub_name is not None:
                raise ValueError(
                    f"Parsing Error: Multiple strt_hubs detected, "
                    f"line {self.line_num}")
            self.start_hub_name = zone.name
            if "max_drones" not in line_clean:
                zone.max_drones = self.drone_nbr
            self.max_capacity_start = zone.max_drones

        elif line_clean.startswith("end_hub:"):
            if self.end_hub_name is not None:
                raise ValueError(
                    f"Parsing Error: Multiple end_hubs detected, "
                    f"line {self.line_num}")
            self.end_hub_name = zone.name
            if "max_drones" not in line_clean:
                zone.max_drones = self.drone_nbr
            self.max_capacity_finish = zone.max_drones

        self.drone_map.zone_map[zone.name] = zone

    def _handle_connection_line(self, line: str) -> None:
        """Parse one connection line and register it on `drone_map`.

        Args:
            line: Raw line of text from the map file.

        Raises:
            ValueError: If either endpoint zone is undefined, or if the
                connection duplicates one already registered (in either
                direction).
        """
        connection = parse_connection(line, self.line_num)

        if connection.zone_start not in self.drone_map.zone_map:
            raise ValueError(
                f"Parsing Error: Zone '{connection.zone_start}' "
                f"is not defined, line {self.line_num}")
        if connection.zone_finish not in self.drone_map.zone_map:
            raise ValueError(
                f"Parsing Error: Zone '{connection.zone_finish}' "
                f"is not defined, line {self.line_num}")

        for existing_conn in self.drone_map.connection_map:
            ex_start = existing_conn.zone_start
            ex_finish = existing_conn.zone_finish
            c_start = connection.zone_start
            c_finish = connection.zone_finish

            match_direct = ex_start == c_start and ex_finish == c_finish
            match_inverted = ex_start == c_finish and ex_finish == c_start

            if match_direct or match_inverted:
                raise ValueError(
                    "Parsing Error: Duplicate connection between "
                    f"'{connection.zone_start}' "
                    f"and '{connection.zone_finish}', "
                    f"line {self.line_num}")

        self.drone_map.connection_map.append(connection)

    def _validate_hubs(self) -> None:
        """Validate that the start/end hubs are well-formed as a pair.

        Raises:
            ValueError: If either hub is missing, if they are the same
                zone, or if the drone count exceeds either hub's
                capacity.
        """
        if self.start_hub_name is None:
            raise ValueError(
                "Parsing Error: Missing 'start_hub:' zone in the file"
                )

        if self.end_hub_name is None:
            raise ValueError(
                "Parsing Error: Missing 'end_hub:' zone in the file"
                )

        if self.start_hub_name == self.end_hub_name:
            raise ValueError(
                "Parsing Error: 'start_hub' and 'end_hub' "
                f"cannot be the same ('{self.start_hub_name}')")

        exceeds_finish = self.drone_nbr > self.max_capacity_finish
        exceeds_start = self.drone_nbr > self.max_capacity_start

        if exceeds_finish and exceeds_start:
            raise ValueError(
                "Parsing Error: Drone number is greater "
                "than start_hub and finish_hub capacity"
                )
        elif exceeds_finish:
            raise ValueError(
                "Parsing Error: Drone number is greater "
                "than finish_hub capacity"
                )
        elif exceeds_start:
            raise ValueError(
                "Parsing Error: Drone number is greater "
                "than start_hub capacity"
                )


def map_creation() -> tuple[DroneMap, bool]:
    """Parse the map file given on the command line into a `DroneMap`.

    Thin backward-compatible wrapper around `MapParser`, kept so existing
    callers (e.g. `fly_in.py`) do not need to change.

    Returns:
        A tuple of the fully populated `DroneMap` and the
        `capacity_info` flag.

    Raises:
        UsageError: If the command line does not contain exactly one
            positional argument (the map file path).
        MissingDroneNumber: If the file has no ``nb_drones:`` line before
            any other content.
        DroneNumberError: If the drone number is missing, not a valid
            integer, not positive, or exceeds the allowed maximum.
        ValueError: For any other parsing error.
        FileNotFoundError: If the given map file path does not exist.
    """
    return MapParser.from_argv().parse()
