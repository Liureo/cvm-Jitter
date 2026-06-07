from __future__ import annotations

import math


PATTERN_IDS = (
    "upper_left",
    "upper_right",
    "horizontal",
    "lower_left",
    "lower_right",
    "circle",
)


def build_pattern(pattern_id: str, amplitude: int) -> list[tuple[int, int]]:
    amplitude = max(1, int(amplitude))
    directions = {
        "upper_left": (-amplitude, -amplitude),
        "upper_right": (amplitude, -amplitude),
        "horizontal": (amplitude, 0),
        "lower_left": (-amplitude, amplitude),
        "lower_right": (amplitude, amplitude),
    }
    if pattern_id in directions:
        x, y = directions[pattern_id]
        return [(x, y), (-x, -y)]

    if pattern_id == "circle":
        points = [(0, 0)]
        steps = 16
        for step in range(steps):
            angle = (2.0 * math.pi * step) / steps
            points.append(
                (
                    round(math.cos(angle) * amplitude),
                    round(math.sin(angle) * amplitude),
                )
            )
        points.append((0, 0))
        return [
            (current[0] - previous[0], current[1] - previous[1])
            for previous, current in zip(points, points[1:])
        ]

    raise ValueError(f"Unknown jitter pattern: {pattern_id}")
