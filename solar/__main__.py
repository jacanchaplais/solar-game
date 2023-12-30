import math
from pathlib import Path
import cmath
import collections as cl
import functools as fn
import operator as op
import sys
import random
import itertools as it
import typing as ty
import contextlib as ctx

import pygame

from . import CONST, COLOR, SIM, load_conf


T = ty.TypeVar("T")

TIMESTEP = CONST["SECONDS_PER_DAY"] * SIM["days_per_timestep"]
SOLAR_MASS = CONST["SOLAR_MASS"]
GRAV_CONST = CONST["GRAV_CONST"]
AU = CONST["AU"]
LIGHTYEARS_PER_AU = 1.057E-16
COLOR_WHITE = COLOR["white"]

SCALE_PER_AU = 200.0

KEY_TEXT = (
    "Press q or ESC to exit",
    "Press d to turn on / off distance",
    "Press s to turn on / off drawing orbit lines",
    "Use hjkl or arrow keys to move around",
    "Press c to center",
    "Press Space to pause / unpause",
    "Use - / + to zoom, and 0 to reset",
)


class Body:
    __slots__ = (
        "name",
        "pos",
        "vel",
        "radius",
        "color",
        "mass",
        "_GM",
        "orbit",
    )

    def __init__(
        self,
        name: str,
        x: float,
        y: float,
        vel_x: float,
        vel_y: float,
        radius: float,
        color: tuple[int, int, int],
        mass: float,
    ) -> None:
        self.name = name
        self.pos = complex(x, y)
        self.vel = complex(vel_x, vel_y)
        self.radius = radius
        self.color = color
        self.mass = mass
        self._GM = mass * GRAV_CONST
        period = math.tau * math.sqrt(
            pow(abs(x), 3) / (GRAV_CONST * SOLAR_MASS)
        )
        self.orbit = cl.deque(maxlen=math.ceil(period / TIMESTEP))

    @property
    def x_vel(self) -> float:
        return self.vel.real

    @property
    def y_vel(self) -> float:
        return self.vel.imag

    def distance_to(self, body: ty.Self) -> float:
        return abs(self.pos - body.pos)

    def attraction(self, other: ty.Self) -> complex:
        displacement = other.pos - self.pos
        distance, theta = cmath.polar(displacement)
        force = self._GM * other.mass / (distance * distance)
        force = cmath.rect(force, theta)
        return force

    def update_position(self, bodies: ty.Iterable[ty.Self]) -> None:
        total_force = complex(0.0, 0.0)
        for body in filter(lambda b: b is not self, bodies):
            total_force += self.attraction(body)
        self.vel += total_force * TIMESTEP / self.mass
        self.pos += self.vel * TIMESTEP
        self.orbit.append((self.pos.real, self.pos.imag))

    def update_scale(self, factor: float) -> None:
        self.radius *= factor


def coord_disp(
    x: float, y: float, scale: float, move_x: float = 0.0, move_y: float = 0.0
) -> tuple[float, float]:
    half_width = 0.5 * pygame.display.Info().current_w
    half_height = 0.5 * pygame.display.Info().current_h
    return (x * scale + half_width + move_x, y * scale + half_height + move_y)


def draw(
    body: Body,
    sun: Body,
    window: pygame.Surface,
    scale: float,
    show: bool,
    move_x: float,
    move_y: float,
    draw_line: bool,
    display_dist: bool,
    font: pygame.font.Font,
    color: tuple[int, int, int] = COLOR_WHITE,
    num_segments: int = 1000,
) -> None:
    coord_ = fn.partial(coord_disp, scale=scale, move_x=move_x, move_y=move_y)
    x, y = coord_(body.pos.real, body.pos.imag)
    pygame.draw.circle(window, body.color, (x, y), body.radius)
    if draw_line and ((num_points := len(body.orbit)) > 2):
        stride = (num_points // num_segments) + 1
        orbit_points = it.islice(body.orbit, None, None, stride)
        traj = tuple(it.starmap(coord_, orbit_points))
        pygame.draw.aalines(window, body.color, False, traj, 1)
    if not (display_dist and show):
        return
    distance = body.distance_to(sun) * LIGHTYEARS_PER_AU
    distance_text = font.render(f"{distance:.2e} light years", True, color)
    window.blit(
        distance_text,
        (
            x - 0.5 * distance_text.get_width(),
            y - 0.5 * distance_text.get_height() - 20.0,
        ),
    )


def key_message(
    message: str,
    index: int,
    window: pygame.Surface,
    font: pygame.font.Font,
    color: tuple[int, int, int] = COLOR_WHITE,
) -> None:
    offset = 15 + (index * 30)
    window.blit(font.render(message, True, color), (15, offset))


def game_loop(
    window: pygame.Surface, scale: float, bodies: list[Body], fps: int = 60
) -> ty.Iterator[tuple[bool, bool, bool, float, tuple[float, float]]]:
    clock = pygame.time.Clock()
    color_universe = COLOR["universe"]
    scale_factors = {pygame.K_EQUALS: 1.25, pygame.K_MINUS: 0.75}

    # interface switches:
    run = True
    pause = False
    show_distance = False
    draw_line = True

    font = pygame.font.SysFont("Trebuchet MS", 21)
    key_key = fn.partial(key_message, window=window, font=font)

    move_x = move_y = 0.0

    while run:
        clock.tick(fps)
        window.fill(color_universe)
        recentre = False
        rescale = False
        factor = None
        for event in pygame.event.get():
            if not run:
                break
            if event.type != pygame.KEYDOWN:
                run = not (event.type == pygame.QUIT)
                continue
            pressed_key = event.key
            run = not (
                (pressed_key == pygame.K_q) or (pressed_key == pygame.K_ESCAPE)
            )
            pause ^= pressed_key == pygame.K_SPACE
            show_distance ^= pressed_key == pygame.K_d
            draw_line ^= pressed_key == pygame.K_s
            recentre = pressed_key == pygame.K_c
            rescale = pressed_key == pygame.K_0
            factor = scale_factors.get(pressed_key, None)
        if factor:
            scale *= factor
            for body in bodies:
                body.update_scale(factor)
        elif rescale:
            factor = SCALE_PER_AU / (scale * AU)
            scale *= factor
            for body in bodies:
                body.update_scale(factor)
        if recentre:
            move_x, move_y = op.attrgetter("real", "imag")(
                -bodies[0].pos * scale
            )

        yield pause, show_distance, draw_line, scale, (move_x, move_y)

        keys = pygame.key.get_pressed()
        distance = 10
        if keys[pygame.K_LEFT] or keys[pygame.K_h]:
            move_x += distance
        if keys[pygame.K_RIGHT] or keys[pygame.K_l]:
            move_x -= distance
        if keys[pygame.K_UP] or keys[pygame.K_k]:
            move_y += distance
        if keys[pygame.K_DOWN] or keys[pygame.K_j]:
            move_y -= distance
        key_key(f"FPS: {int(clock.get_fps())}", 0)
        for idx, msg in enumerate(KEY_TEXT, start=1):
            key_key(msg, idx)
        for idx, body in enumerate(bodies, start=(len(KEY_TEXT) + 2)):
            key_key(f"- {body.name.capitalize()}", idx, color=body.color)
        pygame.display.update()


class GameContext(ctx.ContextDecorator):
    def __init__(self, title: str) -> None:
        self.title = title

    def __enter__(self: ty.Self) -> ty.Self:
        pygame.init()
        pygame.display.set_caption(self.title)
        return self

    def __exit__(self, *_) -> ty.Literal[False]:
        pygame.quit()
        return False


@GameContext("Solar System Simulation")
def main(conf: dict[str, ty.Any]) -> None:
    # pygame program variables:
    window = pygame.display.set_mode()
    font = pygame.font.SysFont("Trebuchet MS", 16)

    # constants and units:
    scale = SCALE_PER_AU / AU
    unit_speed = AU / CONST["SECONDS_PER_DAY"]
    solar_mass = CONST["SOLAR_MASS"]

    # populating and sorting the bodies from the config file:
    bodies = []
    for name, props in conf["bodies"].items():
        rot_op = cmath.rect(1.0, random.uniform(0.0, math.tau))
        body = Body(
            name=name,
            x=-props["distance"] * AU,
            y=0.0,
            vel_x=0.0,
            vel_y=props["speed"] * unit_speed,
            radius=props["radius"] * AU * scale,
            color=COLOR[name],
            mass=props["mass"] * solar_mass,
        )
        body.pos *= rot_op
        body.vel *= rot_op
        bodies.append(body)
    bodies.sort(key=lambda b: abs(b.pos))
    sun = bodies[0]
    if sun is not next(filter(lambda b: b.name.lower() == "sun", bodies)):
        raise ValueError("Sun is not at the origin.")

    for pause, show_dist, draw_l, scale, shift in game_loop(
        window, scale, bodies, fps=100
    ):
        for body_num, body in enumerate(bodies):
            not_sun = body_num != 0
            draw(
                body,
                sun,
                window,
                scale,
                show_dist,
                shift[0],
                shift[1],
                draw_l,
                not_sun,
                font,
            )
            if pause:
                continue
            body.update_position(bodies)


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    config_path = script_dir / "../config.toml"
    with open(config_path, "rb") as f:
        conf = load_conf(f)
    sys.exit(main(conf))
