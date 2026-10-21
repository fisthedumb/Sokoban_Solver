"""Student entry point. See README.md for the API and scoring rules."""

import time 
import heapq
from itertools import count
from sokoban import sokoban_goal_state

def h(state):
    return sum(
        min(abs(bx - gx) + abs(by - gy) for gx, gy in state.storage)
        for bx, by in state.boxes
    )


def f(state):
    return state.gval + h(state)


def solve(initial_state, timebound=120):
    """Return a goal SokobanState with a valid parent chain, or False."""

    deadline = time.monotonic() + timebound

    order = count()
    frontier = [(f(initial_state), next(order), initial_state)]
    best_g = {initial_state.hashable_state(): initial_state.gval}

    while frontier:
        if time.monotonic() >= deadline:
            return False

        _, _, current = heapq.heappop(frontier)
        if current.gval != best_g[current.hashable_state()]:
            continue
        
        if sokoban_goal_state(current):
            return current
        
        for child in current.successors():
            key = child.hashable_state()

            if child.gval < best_g.get(key, float("inf")):
                best_g[key] = child.gval
                heapq.heappush(frontier, (f(child), next(order), child))
    return False

    raise NotImplementedError("Implement your Sokoban solver")
