from .settings import Settings
from .gcode import CNC_Gcode

from collections import deque
import math

def order_loop_path(pixels):
    if not pixels:
        return []

    pixel_set = set(pixels)
    visited = set()
    path = [pixels[0]]
    visited.add(pixels[0])

    def get_neighbors(p):
        x, y = p
        return [(x + dx, y + dy) for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]]

    def direction(a, b):
        return (b[0] - a[0], b[1] - a[1])

    def similarity(dir1, dir2):
        return dir1[0] * dir2[0] + dir1[1] * dir2[1]

    prev_dir = None

    while True:
        current = path[-1]
        neighbors = [n for n in get_neighbors(current) if n in pixel_set]

        if not neighbors:
            break

        if len(path) > (len(pixel_set) * 2):
            return [(0, 0)] # raise Exception("Tool is too big for this")

        # Prioritize unvisited first
        unvisited_neighbors = [n for n in neighbors if n not in visited]

        candidates = unvisited_neighbors if unvisited_neighbors else neighbors

        if not candidates:
            break

        if prev_dir:
            candidates.sort(key=lambda n: -similarity(prev_dir, direction(current, n)))

        next_pixel = candidates[0]
        path.append(next_pixel)
        visited.add(next_pixel)
        prev_dir = direction(current, next_pixel)

        if next_pixel == path[0] and len(path) > 5:
            break

    return path


def group_sections(outline):
    pixels = outline.load()
    width, height = outline.size
    visited = set()
    groups = []
    group_centers = []

    def neighbors(x, y):
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    yield (nx, ny)

    def dfs(start_x, start_y):
        x_total = 0
        y_total = 0

        stack = deque([(start_x, start_y)])
        group = []

        while stack:
            x, y = stack.pop()
            if (x, y) in visited:
                continue

            x_total += x
            y_total += y
            visited.add((x, y))
            group.append((x, y))

            for nx, ny in neighbors(x, y):
                if pixels[nx, ny] == 0 and (nx, ny) not in visited:
                    stack.append((nx, ny))

        if len(group) == 0:
            return [], (-1, -1)

        return group, (x_total / len(group), y_total / len(group))

    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0 and (x, y) not in visited:
                group, center = dfs(x, y)
                if group:
                    groups.append(group)
                    group_centers.append(center)

    return groups, group_centers



def image_to_tool_path(outline, settings: Settings):
    print("Generating Tool path", end="")
    gcode = CNC_Gcode(settings)
    groups, centers = group_sections(outline)

    x, y = 0, 0
    while len(groups) > 0:
        distance_squared = math.inf
        group_index = 0

        for i in range(len(groups)):
            group_dist = (x-centers[i][0]) ** 2 + (y-centers[i][1]) ** 2

            if group_dist < distance_squared:
                distance_squared = group_dist
                group_index = i

        centers.pop(group_index)
        group = groups.pop(group_index)


        print(f"\rOrdering Pixels for Group: {group_index} ({len(group)} Pixels) ({len(groups)} Left)", end="")

        pixels = order_loop_path(group)

        print(f"\rCreating tool path for Group: {group_index} ({len(groups)} Left)", end="")

        start = pixels[-1]
        gcode.go_to(start[0], start[1], settings.travel_height)
        gcode.spin()

        for x, y in pixels:
            gcode.cut_to(x, y, settings.cut_height)

        gcode.stop()
        gcode.go_to(start[0], start[1], settings.travel_height)
        x, y = start

    print("\n")
    return gcode.gcode