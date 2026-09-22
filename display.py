from map_creator import DroneMap, ZoneTypes


class MapRenderer:
    """Renders a `DroneMap` as a colored grid in the terminal.

    Encapsulates both the static color/symbol lookup tables and the
    grid-layout logic needed to turn a map's zones into a printable,
    colored representation.

    Attributes:
        drone_map: The parsed map whose zones will be displayed.
    """

    COLOR_CODES = {
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        "orange": "38;5;208",
    }

    SYMBOLS = {
        ZoneTypes.NORMAL: "■",
        ZoneTypes.BLOCKED: "✕",
        ZoneTypes.RESTRICTED: "▲",
        ZoneTypes.PRIORITY: "●",
    }

    def __init__(self, drone_map: DroneMap) -> None:
        self.drone_map = drone_map

    def get_ansi_color(self, color_name: str | None) -> str:
        """Look up the ANSI color code for a zone's color tag.

        Args:
            color_name: The color name from the zone's metadata (case
                insensitive), or `None` if the zone has no color set.

        Returns:
            The ANSI color code string matching `color_name`, or the
            code for white if `color_name` is `None` or not recognized.
        """
        default_color = self.COLOR_CODES["white"]
        if color_name is None:
            return default_color
        return self.COLOR_CODES.get(color_name.lower(), default_color)

    def colorize(self, text: str, color_name: str | None) -> str:
        """Wrap text in the ANSI escape codes for a given color.

        Args:
            text: The text to colorize.
            color_name: The color name to look up via `get_ansi_color`.

        Returns:
            `text` wrapped in the matching ANSI color code and reset
            code.
        """
        code = self.get_ansi_color(color_name)
        return f"\033[{code}m{text}\033[0m"

    def get_form_symbol(self, zone_type: ZoneTypes) -> str:
        """Get the display symbol used to represent a zone type.

        Args:
            zone_type: The zone type to look up.

        Returns:
            The single-character symbol associated with `zone_type`.
        """
        return self.SYMBOLS[zone_type]

    def _build_grid_matrix(
            self,
            min_x: int,
            min_y: int,
            grid_width: int,
            grid_height: int,
            cell_width: int,
            ) -> list[list[tuple[str, str] | None]]:
        """Build an empty grid and fill it with each zone's colored cell.

        Args:
            min_x: Smallest x coordinate among all zones, used to
                offset zones into a zero-based grid.
            min_y: Smallest y coordinate among all zones, used to
                offset zones into a zero-based grid.
            grid_width: Number of columns in the grid.
            grid_height: Number of rows in the grid.
            cell_width: Width, in characters, reserved for each cell.

        Returns:
            A `grid_height` by `grid_width` matrix where each populated
            cell holds a tuple of (colored symbol, colored name), and
            empty cells hold `None`.
        """
        map_matrix: list[list[tuple[str, str] | None]] = []
        for y in range(grid_height):
            row: list[tuple[str, str] | None] = []
            for x in range(grid_width):
                row.append(None)
            map_matrix.append(row)

        for zone in self.drone_map.zone_map.values():
            symbol = self.get_form_symbol(zone.zone_type)
            symbol_centered = symbol.center(cell_width)
            name_centered = zone.name.center(cell_width)
            symbol_colored = self.colorize(symbol_centered, zone.color)
            name_colored = self.colorize(name_centered, zone.color)

            grid_y = zone.coord_y - min_y
            grid_x = zone.coord_x - min_x
            map_matrix[grid_y][grid_x] = (symbol_colored, name_colored)

        return map_matrix

    def _print_grid(
            self,
            map_matrix: list[list[tuple[str, str] | None]],
            cell_width: int,
            ) -> None:
        """Print the grid matrix, two lines (symbol, name) per row.

        Args:
            map_matrix: The grid built by `_build_grid_matrix`.
            cell_width: Width, in characters, reserved for each cell.
        """
        for row in reversed(map_matrix):
            symbol_line_parts = []
            name_line_parts = []
            for cell in row:
                if cell is None:
                    symbol_line_parts.append(" " * cell_width)
                    name_line_parts.append(" " * cell_width)
                else:
                    symbol_colored, name_colored = cell
                    symbol_line_parts.append(symbol_colored)
                    name_line_parts.append(name_colored)
            print("   ".join(symbol_line_parts))
            print("   ".join(name_line_parts))
            print()

    def display(self) -> None:
        """Print a colored grid representation of the drone network.

        Lays out every zone on a grid according to its coordinates,
        printing two lines per row: the zone's type symbol and its name,
        both colored according to the zone's `color` metadata.
        """
        zones = self.drone_map.zone_map.values()
        max_x = max(zone.coord_x for zone in zones)
        max_y = max(zone.coord_y for zone in zones)
        min_y = min(zone.coord_y for zone in zones)
        min_x = min(zone.coord_x for zone in zones)
        cell_width = max(len(zone.name) for zone in zones) + 2

        grid_width = max_x - min_x + 1
        grid_height = max_y - min_y + 1

        map_matrix = self._build_grid_matrix(
            min_x, min_y, grid_width, grid_height, cell_width
            )
        self._print_grid(map_matrix, cell_width)


def display_static_map(drone_map: DroneMap) -> None:
    """Print a colored grid representation of the drone network.

    Thin backward-compatible wrapper around `MapRenderer`, kept so
    existing callers (e.g. `fly_in.py`) do not need to change.

    Args:
        drone_map: The parsed map whose zones should be displayed.
    """
    MapRenderer(drone_map).display()
