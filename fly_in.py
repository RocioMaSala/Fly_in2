from dataclasses import dataclass, field
import heapq

from map_creator import DroneMap, ZoneTypes
from map_parsing import map_creation


class NoPathError(Exception):
    """Raised when no valid path exists between a drone's current zone
    and the end zone.

    Args:
        message: Human-readable description of the error.
    """

    def __init__(self, message: str = "Invalid Path") -> None:
        super().__init__(f"{message}")


class SimulationTimeoutError(Exception):
    """Raised when the simulation runs past its maximum allowed turns
    without delivering every drone.

    Args:
        message: Human-readable description of the error.
    """

    def __init__(
        self,
        message: str = "Simulation exceeded maximum turn limit",
    ) -> None:
        super().__init__(message)


@dataclass
class DroneSituation:
    """ The mutable state of a single drone during the simulation.

    Attributes:
        drone_id: unique identifier of the drone.
        actual_position: Name of the zone the drone currently occupies.
        transit_destination: Name of the zone the drone is currently in
            transit toward (used for multi-turn moves into 'restricted' zones),
            or 'None' if the drone is not in transit.
        reached_final_zone: Whether the drone has arrived at the end zone
            and is considered delivered
    """
    drone_id: int
    actual_position: str
    transit_destination: str | None = None
    reached_final_zone: bool = False


@dataclass
class Simulation:
    """Runs the turn_by-turn drone routing simulation over a 'DroneMap'.

    Attributes:
        static_map: The parsed, immutable network of zones and connections
            the simulation runs on.
        drone_list: All drones participating in the simulation, along with
            their current state.
        actual_zone_occupation: Mapping of zone name to the list of drone
            ID's currently occupying it.
        actual_conex_occupation: Mapping of each connection, as a 'frozenset'
            of its two zone names, to the list of drone IDs currently
            traversing it.
        turn_count: Number of turns simulated so far.
        movement_log: One entry per turn, containing the space-separated
            movement notation for every drone that moved that turn."""

    static_map: DroneMap
    drone_list: list[DroneSituation] = field(default_factory=list)
    actual_zone_occupation: dict[str, list[int]] = field(default_factory=dict)
    actual_conex_occupation: dict[frozenset[str], list[int]] = field(
        default_factory=dict
    )
    turn_count: int = 0
    movement_log: list[str] = field(default_factory=list)

    def initialize_drones(self) -> None:
        """Create every drone at the start zone and record its occupancy.
        Populates 'drone_list' with one 'DroneSituation' per drone (using
        'static_map.drone_number'), all starting at the map's 'start_hub'
        zone, and registers them in 'actual_zone_occupation'.
        """
        start_name = ""
        for zone in self.static_map.zone_map.values():
            if zone.start_zone:
                start_name = zone.name
                break
        total_drone_nb = self.static_map.drone_number
        drone_id = 1
        while drone_id <= total_drone_nb:
            drone = DroneSituation(
                drone_id=drone_id,
                actual_position=start_name,
            )
            self.drone_list.append(drone)
            if drone.actual_position not in self.actual_zone_occupation:
                self.actual_zone_occupation[drone.actual_position] = []
            self.actual_zone_occupation[drone.actual_position].append(
                drone.drone_id
            )
            drone_id += 1

    def dijkstra(self, start_name: str) -> tuple[float, list[str]]:
        """Find the cheapest path from a zone to the map's end zone.

        Uses Dijkstra's algorithm over the map's adjacency list, skipping
        'blocked' zones entirely and weighting each destination zone by its
        movement cost ('priority' cheapest, then 'normal', then 'restricted').

        Args:
            start_name: Name of the zone to start the search from.

        Returns:
            A tuple of the total path cost and the list of zone names
            from 'start_name' to the end zone, inclusive of both ends.

        Raises:
            NoPathError: If the end zone is unreachable from 'start_name'
                without crossing a 'blocked' zone.
        """
        end_name = ""
        for zone in self.static_map.zone_map.values():
            if zone.finish_zone:
                end_name = zone.name
                break
        if start_name == end_name:
            return (0.0, [start_name])
        dist = {}
        for key in self.static_map.zone_map.keys():
            dist[key] = float("inf")
        dist[start_name] = 0
        predecessor = {}
        connection_matrix = self.static_map.adjacency()

        heap: list[tuple[float, str]] = []
        heapq.heappush(heap, (0, start_name))
        visited = set()

        while heap:
            current_dist, current_zone = heapq.heappop(heap)
            if current_zone in visited:
                continue
            visited.add(current_zone)

            for dest_zone in connection_matrix.get(current_zone, []):
                zone_info = self.static_map.zone_map[dest_zone]
                if zone_info.zone_type == ZoneTypes.BLOCKED:
                    continue
                if zone_info.zone_type == ZoneTypes.NORMAL:
                    cost = 1.0
                elif zone_info.zone_type == ZoneTypes.PRIORITY:
                    cost = 0.9
                elif zone_info.zone_type == ZoneTypes.RESTRICTED:
                    cost = 2.0
                else:
                    cost = 1.0

                new_distance = current_dist + cost
                if new_distance < dist[dest_zone]:
                    dist[dest_zone] = new_distance
                    predecessor[dest_zone] = current_zone
                    heapq.heappush(heap, (new_distance, dest_zone))

        if dist[end_name] == float("inf"):
            raise NoPathError

        path = []
        current = end_name
        while current != start_name:
            path.append(current)
            current = predecessor[current]
        path.append(start_name)
        path.reverse()
        total_dist = dist[end_name]
        return (total_dist, path)

    def process_turn(self, capacity_info: bool = False) -> None:
        """Advance the simulation by a single turn.

        Recomputes each active drone's shortest path, processes drones
        in order of shortest remaining path first (ties broken by drone ID),
        and attempts to move each one: completing any pending transit into
        a 'restricted' zone, or otherwise advancing toward the next zone on
        its path when zone and connection capacity allow it. Zone/connection
        occupancy and 'movement_log' are updated accordingly.

        Args:
            capacity_info: if 'True', print a per-zone and per-connection
                occupancy report for this turn.
        """
        self.turn_count += 1
        active_drones = [
            drone for drone in self.drone_list if not drone.reached_final_zone
        ]
        temp_dist_path = {}
        turn_movements = []
        link_capacity_map = self.static_map.link_capacity()
        for drone in active_drones:
            try:
                position = drone.actual_position
                temp_dist_path[drone.drone_id] = self.dijkstra(position)
            except NoPathError:
                temp_dist_path[drone.drone_id] = (float("inf"), [])
        active_drones_sorted = sorted(
            active_drones,
            key=lambda drone: (
                temp_dist_path[drone.drone_id][0],
                drone.drone_id,
            ),
        )
        normal_connections_used: list[frozenset[str]] = []
        for drone in active_drones_sorted:
            if drone.transit_destination:
                previous_position = drone.actual_position
                drone.actual_position = drone.transit_destination
                drone.transit_destination = None
                if drone.actual_position not in self.actual_zone_occupation:
                    self.actual_zone_occupation[drone.actual_position] = []
                self.actual_zone_occupation[drone.actual_position].append(
                    drone.drone_id
                )
                self.actual_conex_occupation[
                    frozenset({previous_position, drone.actual_position})
                ].remove(drone.drone_id)
                if self.static_map.zone_map[drone.actual_position].finish_zone:
                    drone.reached_final_zone = True
                turn_movements.append(
                    f"D{drone.drone_id}-{drone.actual_position}"
                    )

            else:
                try:
                    _, path = self.dijkstra(drone.actual_position)
                except NoPathError:
                    continue
                previous_position = drone.actual_position
                next_position = path[1]
                link_key = frozenset(
                    {previous_position, next_position}
                    )
                drones_en_conexion = len(
                    self.actual_conex_occupation.get(link_key, [])
                    )
                max_link = link_capacity_map.get(link_key, 1)
                if drones_en_conexion >= max_link:
                    continue

                next_zone = self.static_map.zone_map[next_position]
                if not next_zone.finish_zone:
                    next_zone_drones = len(
                        self.actual_zone_occupation.get(next_position, [])
                    )
                    if next_zone_drones >= next_zone.max_drones:
                        continue

                if (
                    self.static_map.zone_map[next_position].zone_type
                    == ZoneTypes.RESTRICTED
                ):
                    drone.transit_destination = next_position
                    key = frozenset(
                        {previous_position, drone.transit_destination}
                        )
                    if key not in self.actual_conex_occupation:
                        self.actual_conex_occupation[key] = []
                    self.actual_conex_occupation[key].append(drone.drone_id)
                    self.actual_zone_occupation[previous_position].remove(
                        drone.drone_id
                    )
                    turn_movements.append(
                        f"D{drone.drone_id}-"
                        f"{drone.actual_position}-{drone.transit_destination}"
                    )
                else:
                    drone.actual_position = next_position

                    if link_key not in self.actual_conex_occupation:
                        self.actual_conex_occupation[link_key] = []
                    self.actual_conex_occupation[link_key].append(
                        drone.drone_id
                        )
                    normal_connections_used.append(link_key)

                    pos = drone.actual_position
                    if pos not in self.actual_zone_occupation:
                        self.actual_zone_occupation[drone.actual_position] = []
                    self.actual_zone_occupation[drone.actual_position].append(
                        drone.drone_id
                    )
                    self.actual_zone_occupation[previous_position].remove(
                        drone.drone_id
                    )

                    zone = self.static_map.zone_map[drone.actual_position]
                    if zone.finish_zone:
                        drone.reached_final_zone = True
                    turn_movements.append(
                        f"D{drone.drone_id}-{drone.actual_position}"
                        )

        for link_key in normal_connections_used:
            self.actual_conex_occupation[link_key] = []

        if capacity_info:
            print(f"--- Turn {self.turn_count} capacity info ---")
            for zone_name, drones in self.actual_zone_occupation.items():
                zone = self.static_map.zone_map[zone_name]
                print(f"Zone {zone_name}: "
                      f"{len(drones)}/{zone.max_drones} drones")
            for conn_key, drones in self.actual_conex_occupation.items():
                conn_names = "-".join(sorted(conn_key))
                capacity = self.static_map.link_capacity().get(conn_key, 1)
                print(f"Connection {conn_names}: "
                      f"{len(drones)}/{capacity} capacity used")

        self.movement_log.append(" ".join(turn_movements))

    def run_simulation(self, capacity_info: bool = False) -> None:
        """Run the full simulation until every drone reaches the end zone.

        Initializes all drones at the start zone and repeatedly calls
        'process_turn' until 'reached_final_zone' is 'True' for every
        drone, or the turn limit is exceeded.

        Args:
            capacity_info: if 'True', forwarded to 'process_turn' to print
            per-turn occupancy reports.

        Raises:
            SimulationTimeoutError: If the simulation exceeds 1000 turns
                without delivering every drone.
        """
        self.initialize_drones()
        max_turns = 1000
        while not all(drone.reached_final_zone for drone in self.drone_list):
            self.process_turn(capacity_info)
            if self.turn_count > max_turns:
                raise SimulationTimeoutError(
                    f"Simulation exceeded {max_turns} turns without completing"
                )


if __name__ == "__main__":
    from display import display_static_map

    COLORES_ANSI = {
        "green": "\033[32m",
        "yellow": "\033[33m",
        "red": "\033[31m",
        "blue": "\033[34m",
        "cyan": "\033[36m",
        "magenta": "\033[35m",
        "white": "\033[37m",
        "purple": "\033[35;1m",
        "orange": "\033[38;5;208m",
        "brown": "\033[38;5;130m",
        "maroon": "\033[38;5;88m",
        "black": "\033[90m",
        "gold": "\033[33;1m",
        "violet": "\033[35;1m",
        "crimson": "\033[31;1m",
        "darkred": "\033[31m",
        "rainbow": "\033[36;1m",
        "lime": "\033[38;5;118m",
        "gray": "\033[38;5;244m",
        "marron": "\033[38;5;88m",
        "darked": "\033[38;5;52m",
        "reset": "\033[0m",
    }

    try:
        my_map, capacity_info = map_creation()
        display_static_map(my_map)
        simu = Simulation(static_map=my_map)
        simu.run_simulation(capacity_info)
        print(
            "\nMap Key:\n Zone Type Normal -> '■'\n "
            "Zone Type Blocked -> '✕'\n "
            "Zone Type Restricted -> '▲'\n "
            "Zone Type Priority -> '●'"
        )
        print("\nSimulation Finished")
        for turn_number, logro in enumerate(simu.movement_log, start=1):
            if not logro.strip():
                print(f"Turn {turn_number}: No movements")
                continue

            movimientos_coloreados = []

            for mov in logro.split():
                if "-" in mov:
                    drone_part, zone_name = mov.split("-", 1)
                    zone_obj = my_map.zone_map.get(zone_name)

                    color_nombre = getattr(zone_obj, "color", "reset")
                    color_ansi = COLORES_ANSI.get(
                        color_nombre,
                        COLORES_ANSI["reset"],
                    )

                    mov_color = (
                        f"{drone_part}-"
                        f"{color_ansi}{zone_name}{COLORES_ANSI['reset']}"
                    )
                    movimientos_coloreados.append(mov_color)
                else:
                    movimientos_coloreados.append(mov)

            print(f"Turn {turn_number}: {' '.join(movimientos_coloreados)}")

    except Exception as e:
        print(e)
