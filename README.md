*This project has been created as part of the 42 curriculum by romarti2.*

# fly_in: Pathfinding Optimization

## Description
fly_in is a pathfinding and graph optimization project developed as part of the 42 curriculum. The core objective of the project is to calculate the most efficient, shortest path between coordinates or nodes within a custom map network.

By leveraging a highly optimized implementation of Dijkstra's Algorithm, the program parses a given map layout, computes the lowest-cost paths, and ensures reliable navigation from an origin point to a specific destination while strictly handling weights and constraints.

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
For the requirements of fly_in, Dijkstra’s algorithm was selected because it guarantees finding the mathematically shortest path in a weighted graph, provided that all edge weights are non-negative (w≥0).

### Implementation Strategy
- *Graph Traversal & Representation*: The map layout is processed into an adjacency list / coordinate grid, minimizing the memory overhead compared to a traditional matrix.

- *Priority Queue Optimization*: To keep the execution time minimal even on complex maps, a custom Min-Heap structure was implemented. This optimizes the time complexity of extracting the minimum distance node.

- *Robust Error Management*: The parser checks for invalid maps, open boundaries, unreachable goals, and invalid formatting before passing data to the pathfinder, guaranteeing a clean exit without segmentation faults.


## Resources
Documentation & References
- Dijkstra's Algorithm - Wikipedia - Foundational reference for shortest-path mechanics.

- Peer to Peer

## AI Usage Disclosure
Artificial Intelligence models were utilized during the creation of this project for the following specific tasks:

- Code Refactoring.

- Documentation Architecture: Used to format, translate, and organize this README.md