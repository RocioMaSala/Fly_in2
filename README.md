*This project has been created as part of the 42 curriculum by romarti2.*

# fly_in: Pathfinding Optimization

## Description
fly_in is a multi-drone routing and scheduling simulation developed as part of
the 42 curriculum. Given a map of interconnected zones and a fleet of drones
starting at a shared base, the program computes a turn-by-turn schedule that
routes **every drone simultaneously** from the start zone to the end zone in
the fewest possible simulation turns.

Unlike a simple single-path shortest-path problem, fly_in must account for
per-zone movement costs (normal, priority, restricted, blocked), zone and
connection capacity limits, and multi-turn transit through restricted zones —
all while avoiding collisions and deadlocks between drones sharing the same
network. The program parses a custom map format, runs the scheduling
simulation, and reports both a colored visual layout of the network and a
step-by-step log of every drone's movements.

## Instructions

### Prerequisites
- Python: Version 3.10 or later is strictly required.
- Quality & Standards: The codebase adheres to the flake8 coding standard and uses mypy for mandatory, static type safety.

### Installation
To install the required environment dependencies, run: *make install*

### Execution
To execute the main simulation interpreter: *make run*

To run the project in debug mode utilizing Python's built-in debugger (pdb): *make debug*

To cear temporary caches, pre-compiled bytecode (pycache), or mypy artifacts: *make clean*

### Linting & Static Typing
To verify code compliance using flake8 and strict mypy checks: *make lint*


## Algorithm Choices & Implementation Strategy

### Why Dijkstra's Algorithm?
Dijkstra's algorithm was chosen to compute each drone's shortest path because
it guarantees the mathematically optimal path in a weighted graph with
non-negative edge weights (w≥0) — which fits this problem, since zone
movement costs (1 for normal/priority, 2 for restricted) are always positive.
Priority zones are additionally weighted slightly cheaper than normal zones
so the algorithm favors them when multiple equal-length routes exist, as the
subject recommends.

### Multi-Drone Turn Scheduling
Finding a single shortest path is not enough, since drones move
simultaneously and must not violate capacity or collide. Each simulation
turn:

1. Every active (not yet delivered) drone's shortest path to the goal is
   recomputed from its current position, so the schedule adapts as zones and
   connections free up.
2. Drones are processed in order of **shortest remaining path first** (ties
   broken by drone ID), so the closest drones to delivery are given priority
   when capacity is contested.
3. Before a drone moves, its destination zone and the connection it would use
   are checked against their current occupancy: `max_drones` for zones and
   `max_link_capacity` for connections. If either is full, the drone waits
   in place for this turn instead of moving.
4. If the destination is a `restricted` zone, the drone enters a two-turn
   transit state: it occupies the connection (not the destination zone) for
   one turn, then is guaranteed to arrive on the next turn — it cannot wait
   partway through a restricted transit.
5. Drones that reach the end zone are marked as delivered and excluded from
   further scheduling.

This turn-based, capacity-aware scheduling is what prevents collisions and
deadlocks between drones sharing the same zones and connections, while still
aiming to minimize the total number of turns.

### Implementation Strategy
- **Graph Traversal & Representation**: The map is parsed into an adjacency
  list (`DroneMap.adjacency()`), which is more memory-efficient than an
  adjacency matrix for sparse networks.
- **Priority Queue**: Dijkstra's minimum-distance extraction is implemented
  using Python's built-in `heapq` module, giving each extraction O(log n)
  complexity.
- **Robust Error Management**: The parser validates zone/connection syntax,
  metadata, capacities, and required start/end hubs before any pathfinding
  occurs, raising descriptive errors (with line numbers) rather than
  crashing or silently producing an invalid simulation.

## Visual Representation

Before the simulation starts, the program renders a static map of the network as
a colored grid, positioned according to each zone's `(x, y)` coordinates.
Each zone is displayed with:

- A **symbol** indicating its type: `■` normal, `✕` blocked, `▲` restricted,
  `●` priority.
- Its **name**, printed below the symbol.
- A **color**, taken from the zone's `color` metadata (e.g. green for the
  start hub, yellow for the end hub, red for restricted zones), using ANSI
  terminal escape codes.

During the simulation, every turn's drone movements are printed as a line in
the format `D<id>-<zone>`, with the destination zone name colored to match
its map color. This lets you visually track, turn by turn, which drones
are moving through which type of zone (e.g. spotting red/restricted
segments where extra turns are being spent) without needing to cross-reference
the static map separately.

This combination — a colored spatial overview plus colored turn-by-turn
logs — makes it easier to spot bottlenecks (e.g. many drones queuing at a
low-capacity zone) and to sanity-check that the simulation respects zone
types, at a glance, without reading raw coordinates or type labels.

## Example Input and Output

**Input** (`maps/example/map.txt`):

\```
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal

\```

Run with:

\```bash
make run MAP=maps/example/map.txt
\```

**Output** (simulation log, colors omitted here for readability):

\```
Simulation Finished
Turn 1: D1-waypoint1
Turn 2: D1-waypoint2 D2-waypoint1
Turn 3: D1-goal D2-waypoint2
Turn 4: D2-goal
\```

## Resources
Documentation & References
- Dijkstra's Algorithm - Wikipedia - Foundational reference for shortest-path mechanics.

- Peer to Peer

## AI Usage Disclosure
Artificial Intelligence models were utilized during the creation of this project for the following specific tasks:

- Code Refactoring.

- Documentation Architecture: Used to format, translate, and organize this README.md

All AI-assisted code and documentation were reviewed, tested, and validated
by the author, who can explain and justify every part of the implementation
during peer review.