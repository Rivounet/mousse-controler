"""Pure, seeded trajectory generation with no hardware dependency."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

from .geometry import DesktopTopology, Point


@dataclass(frozen=True)
class TrajectoryConfig:
    spacing_px: float = 32.0
    curvature: float = 0.12
    speed_variation: float = 0.04
    micro_variation_px: int = 1
    minimum_points: int = 3
    maximum_points: int = 10

    def __post_init__(self) -> None:
        if (self.spacing_px <= 0 or self.minimum_points < 2 or
                self.maximum_points < self.minimum_points):
            raise ValueError("invalid trajectory sampling")
        if not -0.5 <= self.curvature <= 0.5:
            raise ValueError("curvature outside safe range")
        if not 0 <= self.speed_variation <= 0.15:
            raise ValueError("speed variation outside safe range")
        if not 0 <= self.micro_variation_px <= 3:
            raise ValueError("micro variation outside safe range")


class TrajectoryEngine:
    def __init__(self, config: TrajectoryConfig | None = None):
        self.config = config or TrajectoryConfig()

    def generate(
        self,
        start: Point,
        target: Point,
        topology: DesktopTopology,
        rng: random.Random,
    ) -> list[Point]:
        if not topology.contains(start) or not topology.contains(target):
            raise ValueError("trajectory endpoints must be on the physical desktop")
        dx, dy = target[0] - start[0], target[1] - start[1]
        distance = math.hypot(dx, dy)
        if distance == 0:
            return [target]
        count = min(
            self.config.maximum_points,
            max(self.config.minimum_points, math.ceil(distance / self.config.spacing_px)),
        )
        midpoint = ((start[0] + target[0]) / 2, (start[1] + target[1]) / 2)
        perpendicular = (-dy / distance, dx / distance)
        bend = distance * self.config.curvature * rng.uniform(-1.0, 1.0)
        control = (midpoint[0] + perpendicular[0] * bend, midpoint[1] + perpendicular[1] * bend)
        points: list[Point] = []
        previous_u = 0.0
        phase = rng.random() * 2 * math.pi
        for index in range(1, count + 1):
            t = index / count
            smooth = t * t * (3 - 2 * t)  # progressive acceleration/deceleration
            variation = self.config.speed_variation * math.sin(2 * math.pi * t + phase) * t * (1 - t)
            u = max(previous_u, min(1.0, smooth + variation))
            previous_u = u
            inverse = 1 - u
            x = inverse * inverse * start[0] + 2 * inverse * u * control[0] + u * u * target[0]
            y = inverse * inverse * start[1] + 2 * inverse * u * control[1] + u * u * target[1]
            if index != count and self.config.micro_variation_px:
                x += rng.randint(-self.config.micro_variation_px, self.config.micro_variation_px)
                y += rng.randint(-self.config.micro_variation_px, self.config.micro_variation_px)
            point = topology.nearest_point((round(x), round(y)))
            if not points or point != points[-1]:
                points.append(point)
        if not points or points[-1] != target:
            points.append(target)
        return points
