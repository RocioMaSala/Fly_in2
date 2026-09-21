from map_creator import DroneMap, ZoneTypes


def get_ansi_color(color_name: str | None) -> str:
    """ Look up the ANSI color code for a zone's color tag.

    Args:
        color_name: the color name from the zone's metadata
            (case insensitive), or 'None' if the zone has
            no color set.

    Returns:
        The ANSI color code string matching 'color_name', or the code
        for white if 'color_name' is 'None' or not recognized.
    """
    color_dict = {
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        "orange": "\033[38;5;208m",
    }
    default_color = color_dict["white"]
    if color_name is None:
        return default_color
    return color_dict.get(color_name.lower(), default_color)


def colorize(text: str, color_name: str | None) -> str:
    """Wrap text in the ANSI escape codes for a given color.

    Args:
        text: The text to colorize.
        color_name: The color name to look up via 'get_ansi_color'.

    Returns:
        'text' wrapped in the matching ANSI color code and reset code.
    """
    code = get_ansi_color(color_name)
    return f"\033[{code}m{text}\033[0m"


def get_form_symbol(zone_type: ZoneTypes) -> str:
    """Get the display symbol used to represent a zone type.

    Args:
        zone_type: the zone type to look up.

    Returns:
        The single-character symbol associated with 'zone_type'.
    """
    form_type = {
        ZoneTypes.NORMAL: "■",
        ZoneTypes.BLOCKED: "✕",
        ZoneTypes.RESTRICTED: "▲",
        ZoneTypes.PRIORITY: "●",
    }
    return form_type[zone_type]


def display_static_map(drone_map: DroneMap) -> None:
    """Print a colored grid representation of the drone network.

    Lays out every zone on a grid according to its coordinates, printing
    two lines per row: the zone's type symbol an its name, both colored
    according to the zone's 'color' metadata.

    Args:
        drone_map: The parsed map whose zones should be displayed.
    """
    max_x = max(zone.coord_x for zone in drone_map.zone_map.values())
    max_y = max(zone.coord_y for zone in drone_map.zone_map.values())
    min_y = min(zone.coord_y for zone in drone_map.zone_map.values())
    min_x = min(zone.coord_x for zone in drone_map.zone_map.values())
    cell_width = max(
        len(zone.name) for zone in drone_map.zone_map.values()
        ) + 2

    grid_width = max_x - min_x + 1
    grid_height = max_y - min_y + 1

    map_matrix: list[list[tuple[str, str] | None]] = []
    for y in range(grid_height):
        row: list[tuple[str, str] | None] = []
        for x in range(grid_width):
            row.append(None)
        map_matrix.append(row)

    for zone in drone_map.zone_map.values():
        symbol = get_form_symbol(zone.zone_type)
        symbol_centered = symbol.center(cell_width)
        name_centered = zone.name.center(cell_width)
        symbol_colored = colorize(symbol_centered, zone.color)
        name_colored = colorize(name_centered, zone.color)

        grid_y = zone.coord_y - min_y
        grid_x = zone.coord_x - min_x
        map_matrix[grid_y][grid_x] = (symbol_colored, name_colored)

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
