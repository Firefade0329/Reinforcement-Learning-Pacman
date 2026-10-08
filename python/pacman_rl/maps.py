"""Fixed Pacman map (ported cell-for-cell from ReinforcementLearning/Game.java)
plus precomputed topology: neighbour table and all-pairs shortest paths.

Coordinates are (x, y) with x to the right and y downward, exactly as in the
Java code.  Actions/directions are indexed 0..3 = right, down, left, up, i.e.
the Java ``dirSet = {{1,0},{0,1},{-1,0},{0,-1}}``.
"""
from __future__ import annotations

from collections import deque

import numpy as np

# '#': wall (255 in Java)   '.': open cell that starts with a gold pellet (1 in Java)
MAP_ROWS = (
    "################################",
    "#.....#####...####...#####.....#",
    "#.###.#.....#......#.....#.###.#",
    "#.###.#.###.#.##.#.#.###.#.###.#",
    "#.....#...#.#......#.#...#.....#",
    "##.##...#.#...##.#...#.#...##.##",
    "##.##.#.#...#......#...#.#.##.##",
    "##......#.#.#.####.#.#.#......##",
    "##.##.#.......####.......#.##.##",
    "##.##.##.#.##......##.#.##.##.##",
    "##.##....#.....##.....#....##.##",
    "##.##.##...###....###...##.##.##",
    "##.##.####.....##.....####.##.##",
    "#.........##.#....#.##.........#",
    "#.#####.#......##......#.#####.#",
    "#.##......####.##.####......##.#",
    "#....#.##.####....####.##.#....#",
    "#.####.##......##......##.####.#",
    "#.......######....######.......#",
    "#.##.##........##........##.##.#",
    "#..#....####.######.####....#..#",
    "##..#.#..##..........##..#.#..##",
    "###...##....########....##...###",
    "################################",
)

H = len(MAP_ROWS)
W = len(MAP_ROWS[0])
DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))  # right, down, left, up

WALL = np.array([[c == "#" for c in row] for row in MAP_ROWS], dtype=bool)

# open cells in row-major order; CELL_ID[y, x] = index or -1 for walls
CELLS = [(x, y) for y in range(H) for x in range(W) if not WALL[y, x]]
N = len(CELLS)
CELL_X = np.array([c[0] for c in CELLS], dtype=np.int16)
CELL_Y = np.array([c[1] for c in CELLS], dtype=np.int16)
CELL_ID = -np.ones((H, W), dtype=np.int32)
for _i, (_x, _y) in enumerate(CELLS):
    CELL_ID[_y, _x] = _i

# NEIGHBOURS[c, d] = cell id reached by moving in direction d from c, or -1 if blocked
NEIGHBOURS = -np.ones((N, 4), dtype=np.int32)
for _i, (_x, _y) in enumerate(CELLS):
    for _d, (_dx, _dy) in enumerate(DIRS):
        NEIGHBOURS[_i, _d] = CELL_ID[_y + _dy, _x + _dx]  # border is all wall, no bounds check needed


def _all_pairs() -> np.ndarray:
    dist = np.full((N, N), -1, dtype=np.int16)
    for s in range(N):
        dist[s, s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in NEIGHBOURS[u]:
                if v >= 0 and dist[s, v] < 0:
                    dist[s, v] = dist[s, u] + 1
                    q.append(v)
    return dist


# DIST[a, b] = shortest path length in steps (ignores ghosts, like the Java BFS)
DIST = _all_pairs()
assert (DIST >= 0).all(), "map must be connected"
