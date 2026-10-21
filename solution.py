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
