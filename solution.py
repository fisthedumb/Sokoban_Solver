"""Student entry point. See README.md for the API and scoring rules."""

import time
from collections import deque
from sokoban import sokoban_goal_state


def solve(initial_state, timebound=120):
    """Return a goal SokobanState with a valid parent chain, or False."""
    deadline = time.monotonic() + timebound
    frontier = deque([initial_state])
    visited = {initial_state.hashable_state()}

    while frontier:
        if time.monotonic() >= deadline:
            return False

        current = frontier.popleft()

        if sokoban_goal_state(current):
            return current

        for child in current.successors():
            key = child.hashable_state()

            if key not in visited:
                visited.add(key)
                frontier.append(child)

    return False

def h(state):
    total = 0
    
    for bx, by in state.boxes:
        distance = min(
            abs(bx - sx) + abs(by - sy)
            for sx, sy in state.storage
        )
        total += distance

    return total
    # raise NotImplementedError("Implement your Sokoban solver")

def f(state):
    return state.gval + h(state)
