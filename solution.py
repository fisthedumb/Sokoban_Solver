"""Student entry point. See README.md for the API and scoring rules."""

import time 
import heapq
from itertools import count
from sokoban import sokoban_goal_state

def solve(initial_state, timebound=120):
    """Return a goal SokobanState with a valid parent chain, or False."""

    deadline = time.monotonic() + timebound

    order = count()
    frontier = [(f(initial_state), next(order), initial_state)]
    best_g = {}
    initial_key = initial_state.hashable_state()
    best_g[initial_key] = initial_state.gval

    while frontier:
        if time.monotonic() >= deadline:
            return False

        item = heapq.heappop(frontier)
        current = item[2]
        current_key = current.hashable_state()
        if current.gval > best_g[current_key]:
            continue        

        if sokoban_goal_state(current):
            return current
        
        for child in current.successors():
            key = child.hashable_state()

            if key in best_g and child.gval >= best_g[key]:
                continue

            best_g[key] = child.gval
            heapq.heappush(frontier, (f(child), next(order), child))
    return False

def h(state):
    total = 0
    
    for bx, by in state.boxes:
        distance = min(abs(bx - sx) + abs(by - sy)
                       for sx, sy in state.storage
                       )
        total += distance
    return total

def f(state):
    return state.gval + h(state)
