"""Validated physical-desktop zones used by trajectory sequences."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Protocol, Sequence


Point = tuple[int, int]


@dataclass(frozen=True)
class Display:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("display dimensions must be positive")

    @property
    def right(self) -> int:
        return self.x + self.width - 1

    @property
    def bottom(self) -> int:
        return self.y + self.height - 1

    def contains(self, point: Point) -> bool:
        return self.x <= point[0] <= self.right and self.y <= point[1] <= self.bottom


@dataclass(frozen=True)
class DesktopTopology:
    displays: tuple[Display, ...]
    generation: str

    def __post_init__(self) -> None:
        if not self.displays:
            raise ValueError("at least one display is required")

    def contains(self, point: Point) -> bool:
        return any(display.contains(point) for display in self.displays)

    def contains_bounds(self, bounds: tuple[int, int, int, int]) -> bool:
        left, top, right, bottom = bounds
        return any(
            display.x <= left <= right <= display.right
            and display.y <= top <= bottom <= display.bottom
            for display in self.displays
        )

    def nearest_point(self, point: Point) -> Point:
        if self.contains(point):
            return point
        candidates = [
            (
                max(display.x, min(display.right, point[0])),
                max(display.y, min(display.bottom, point[1])),
            )
            for display in self.displays
        ]
        return min(candidates, key=lambda p: (p[0] - point[0]) ** 2 + (p[1] - point[1]) ** 2)


class Zone(Protocol):
    def validate(self, topology: DesktopTopology) -> None: ...
    def contains(self, point: Point) -> bool: ...
    def random_point(self, rng: random.Random) -> Point: ...


@dataclass(frozen=True)
class RectangleZone:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("rectangle dimensions must be positive")

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.x + self.width - 1, self.y + self.height - 1

    def validate(self, topology: DesktopTopology) -> None:
        if not topology.contains_bounds(self.bounds):
            raise ValueError("rectangle is not contained in one physical display")

    def contains(self, point: Point) -> bool:
        left, top, right, bottom = self.bounds
        return left <= point[0] <= right and top <= point[1] <= bottom

    def random_point(self, rng: random.Random) -> Point:
        left, top, right, bottom = self.bounds
        return rng.randint(left, right), rng.randint(top, bottom)


@dataclass(frozen=True)
class CircleZone:
    center_x: int
    center_y: int
    radius: int

    def __post_init__(self) -> None:
        if self.radius <= 0:
            raise ValueError("circle radius must be positive")

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        return (
            self.center_x - self.radius,
            self.center_y - self.radius,
            self.center_x + self.radius,
            self.center_y + self.radius,
        )

    def validate(self, topology: DesktopTopology) -> None:
        if not topology.contains_bounds(self.bounds):
            raise ValueError("circle is not contained in one physical display")

    def contains(self, point: Point) -> bool:
        return (point[0] - self.center_x) ** 2 + (point[1] - self.center_y) ** 2 <= self.radius ** 2

    def random_point(self, rng: random.Random) -> Point:
        for _ in range(1000):
            angle = rng.random() * 2 * math.pi
            radius = math.sqrt(rng.random()) * self.radius
            point = (
                round(self.center_x + math.cos(angle) * radius),
                round(self.center_y + math.sin(angle) * radius),
            )
            if self.contains(point):
                return point
        raise RuntimeError("could not sample circle")


def _orientation(a: Point, b: Point, c: Point) -> int:
    value = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    return 0 if value == 0 else (1 if value > 0 else -1)


def _on_segment(a: Point, b: Point, c: Point) -> bool:
    return min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and min(a[1], c[1]) <= b[1] <= max(a[1], c[1])


def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    o1, o2, o3, o4 = _orientation(a, b, c), _orientation(a, b, d), _orientation(c, d, a), _orientation(c, d, b)
    if o1 != o2 and o3 != o4:
        return True
    return (
        (o1 == 0 and _on_segment(a, c, b))
        or (o2 == 0 and _on_segment(a, d, b))
        or (o3 == 0 and _on_segment(c, a, d))
        or (o4 == 0 and _on_segment(c, b, d))
    )


@dataclass(frozen=True)
class PolygonZone:
    vertices: tuple[Point, ...]

    def __init__(self, vertices: Sequence[Point]):
        object.__setattr__(self, "vertices", tuple((int(x), int(y)) for x, y in vertices))
        if len(self.vertices) < 3:
            raise ValueError("polygon needs at least three vertices")
        if len(set(self.vertices)) != len(self.vertices):
            raise ValueError("polygon vertices must be distinct")
        area2 = sum(
            self.vertices[i][0] * self.vertices[(i + 1) % len(self.vertices)][1]
            - self.vertices[(i + 1) % len(self.vertices)][0] * self.vertices[i][1]
            for i in range(len(self.vertices))
        )
        if area2 == 0:
            raise ValueError("polygon area must be non-zero")
        count = len(self.vertices)
        for i in range(count):
            a, b = self.vertices[i], self.vertices[(i + 1) % count]
            for j in range(i + 1, count):
                if j in (i, (i + 1) % count) or (j + 1) % count in (i, (i + 1) % count):
                    continue
                c, d = self.vertices[j], self.vertices[(j + 1) % count]
                if _segments_intersect(a, b, c, d):
                    raise ValueError("self-intersecting polygon")

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        xs = [p[0] for p in self.vertices]
        ys = [p[1] for p in self.vertices]
        return min(xs), min(ys), max(xs), max(ys)

    def validate(self, topology: DesktopTopology) -> None:
        if not topology.contains_bounds(self.bounds):
            raise ValueError("polygon is not contained in one physical display")

    def contains(self, point: Point) -> bool:
        inside = False
        x, y = point
        count = len(self.vertices)
        for i in range(count):
            a = self.vertices[i]
            b = self.vertices[(i + 1) % count]
            if _orientation(a, point, b) == 0 and _on_segment(a, point, b):
                return True
            if (a[1] > y) != (b[1] > y):
                crossing_x = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
                if x < crossing_x:
                    inside = not inside
        return inside

    def random_point(self, rng: random.Random) -> Point:
        left, top, right, bottom = self.bounds
        for _ in range(10_000):
            point = rng.randint(left, right), rng.randint(top, bottom)
            if self.contains(point):
                return point
        raise RuntimeError("could not sample polygon")
