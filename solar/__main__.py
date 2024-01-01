import cmath
import collections as cl
import contextlib as ctx
import functools as fn
import itertools as it
import math
import operator as op
import random
import sys
import typing as ty
from pathlib import Path

import click

with ctx.redirect_stdout(None):
    import pygame

from . import COLOR, CONST, SIM, load_conf

T = ty.TypeVar("T")

TIMESTEP = CONST["SECONDS_PER_DAY"] * SIM["days_per_timestep"]
SOLAR_MASS = CONST["SOLAR_MASS"]
GRAV_CONST = CONST["GRAV_CONST"]
AU = CONST["AU"]
LIGHTYEARS_PER_AU = 1.057e-16
COLOR_WHITE = COLOR["white"]

SCALE_PER_AU = 200.0
SCRIPT_DIR = Path(__file__).parent

KEY_TEXT = (
    "Press q or ESC to exit",
    "Press i to hide / show this text",
    "Press d to turn on / off distance",
    "Press s to turn on / off drawing orbit lines",
    "Use hjkl or arrow keys to move around",
    "Press c to center",
    "Press Space to pause / unpause",
    "Use - / + to zoom, and 0 to reset",
    "Use ] / [ to increase / decrease target FPS",
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
        num_orbit_steps = math.ceil(period / TIMESTEP)
        self.orbit: cl.deque[complex] = cl.deque(maxlen=num_orbit_steps)

    def distance_to(self, body: ty.Self) -> float:
        return abs(body.pos - self.pos)

    def attraction(self, other: ty.Self) -> complex:
        displacement = other.pos - self.pos
        dist_recip = 1.0 / abs(displacement)
        force_mag = self._GM * other.mass * dist_recip * dist_recip
        return force_mag * (displacement * dist_recip)

    def update_position(self, bodies: ty.Iterable[ty.Self]) -> None:
        bodies = filter(lambda b: b is not self, bodies)
        tot_force = sum(map(self.attraction, bodies), start=complex(0.0, 0.0))
        self.vel += tot_force * TIMESTEP / self.mass
        self.pos += self.vel * TIMESTEP
        self.orbit.append(self.pos)

    def update_scale(self, factor: float) -> None:
        self.radius *= factor


def coord_disp(
    pos: complex,
    scale: float,
    half_res: complex,
    shift: complex = complex(0.0, 0.0),
) -> tuple[float, float]:
    return op.attrgetter("real", "imag")(scale * pos + shift + half_res)


def draw(
    body: Body,
    sun: Body,
    window: pygame.Surface,
    scale: float,
    shift: complex,
    half_res: complex,
    show: bool,
    draw_line: bool,
    font: pygame.font.Font,
    color: tuple[int, int, int] = COLOR_WHITE,
    num_segments: int = 1000,
) -> None:
    coord = fn.partial(coord_disp, scale=scale, half_res=half_res, shift=shift)
    x, y = coord(body.pos)
    pygame.draw.circle(window, body.color, (x, y), body.radius)
    if draw_line and ((num_points := len(body.orbit)) > 2):
        stride = (num_points // num_segments) + 1
        orbit_points = it.islice(body.orbit, None, None, stride)
        traj = tuple(map(coord, orbit_points))
        pygame.draw.aalines(window, body.color, False, traj, 1)
    if not (show and (body is not sun)):
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
) -> ty.Iterator[tuple[bool, bool, bool, float, complex, complex]]:
    clock = pygame.time.Clock()
    color_universe = COLOR["universe"]
    scale_factors = {pygame.K_EQUALS: 1.25, pygame.K_MINUS: 0.75}
    rate_factors = {pygame.K_RIGHTBRACKET: 1.25, pygame.K_LEFTBRACKET: 0.75}

    # interface switches:
    run = True
    pause = False
    show_distance = False
    draw_line = True

    font = pygame.font.SysFont("Trebuchet MS", 21)
    key_key = fn.partial(key_message, window=window, font=font)

    shift = complex(0.0, 0.0)
    display_info = True

    while run:
        clock.tick(fps)
        window.fill(color_universe)
        recentre = False
        rescale = False
        factor = fps_factor = None
        toggle_fullscreen = False
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
            fps_factor = rate_factors.get(pressed_key, None)
            toggle_fullscreen ^= pressed_key == pygame.K_f
            display_info ^= pressed_key == pygame.K_i
        if factor:
            scale *= factor
            for body in bodies:
                body.update_scale(factor)
        if fps_factor:
            fps = min(max(10, math.ceil(fps_factor * fps)), 200)
        elif rescale:
            factor = SCALE_PER_AU / (scale * AU)
            scale *= factor
            for body in bodies:
                body.update_scale(factor)
        if toggle_fullscreen:
            pygame.display.toggle_fullscreen()
            toggle_fullscreen = False
        if recentre:
            shift = -bodies[0].pos * scale

        disp_info = pygame.display.Info()
        half_res = 0.5 * complex(disp_info.current_w, disp_info.current_h)
        yield pause, show_distance, draw_line, scale, half_res, shift

        keys = pygame.key.get_pressed()
        distance = 10
        if keys[pygame.K_LEFT] or keys[pygame.K_h]:
            shift += complex(distance, 0.0)
        if keys[pygame.K_RIGHT] or keys[pygame.K_l]:
            shift -= complex(distance, 0.0)
        if keys[pygame.K_UP] or keys[pygame.K_k]:
            shift += complex(0.0, distance)
        if keys[pygame.K_DOWN] or keys[pygame.K_j]:
            shift -= complex(0.0, distance)
        if display_info:
            key_key(f"FPS: {int(clock.get_fps())}, target: {fps}", 0)
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
        icon = pygame.image.load(SCRIPT_DIR / "../icon.jpg")
        pygame.display.set_icon(icon)
        return self

    def __exit__(self, *_) -> ty.Literal[False]:
        pygame.quit()
        return False


@click.command
@click.option(
    "-r",
    "--resolution",
    nargs=2,
    type=click.IntRange(min=360),
    default=(1280, 720),
)
@GameContext("Solar System Simulation")
def main(resolution: tuple[int, int]) -> None:
    with open(SCRIPT_DIR / "../config.toml", "rb") as f:
        conf = load_conf(f)

    # pygame program variables:
    window = pygame.display.set_mode(resolution)
    font = pygame.font.SysFont("Trebuchet MS", 16)

    # constants and units:
    scale = SCALE_PER_AU / AU
    unit_speed = AU / CONST["SECONDS_PER_DAY"]
    solar_mass = CONST["SOLAR_MASS"]

    # populating and sorting the bodies from the config file:
    bodies: list[Body] = []
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

    for pause, show, draw_l, scale, half_res, shift in game_loop(
        window, scale, bodies, fps=100
    ):
        for body in bodies:
            draw(body, sun, window, scale, shift, half_res, show, draw_l, font)
            if pause:
                continue
            body.update_position(bodies)


if __name__ == "__main__":
    sys.exit(main())
