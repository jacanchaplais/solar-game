import cmath
import collections as cl
import contextlib as ctx
import functools as fn
import io
import itertools as it
import math
import operator as op
import random
import sys
import tomllib
import typing as ty
from fractions import Fraction
from pathlib import Path

import click

with ctx.redirect_stdout(None):
    import pygame

SCRIPT_DIR = Path(__file__).parent

SOLAR_MASS = 1.98892E+30
GRAV_CONST = 6.67428e-11
AU = 1.496E+11  # unit of length
LIGHTYEARS_PER_AU = 1.057e-16
SECONDS_PER_DAY = 86400.0  # unit of time

DAYS_PER_TIMESTEP = 2.0
TIMESTEP = SECONDS_PER_DAY * DAYS_PER_TIMESTEP
SCALE_PER_AU = 200.0

COLOR_WHITE = (255, 255, 255)

KEY_TEXT = (
    "Press q to exit",
    "Press i to hide / show this text",
    "Press d to turn on / off distance",
    "Press s to turn on / off drawing orbit lines",
    "Use hjkl or arrow keys to move around",
    "Press c to center",
    "Press Space to pause / unpause",
    "Use - / + to zoom, and 0 to reset",
    "Use ] / [ to increase / decrease target FPS",
)

T = ty.TypeVar("T")


class TextBox:
    def __init__(self, font: pygame.font.Font, color: pygame.Color) -> None:
        self.active = False
        self._buffer = io.StringIO()
        self.toggled = False
        self.font = font
        self.color = color
        self._box = pygame.Rect(100, 10, 140, 32)

    def __del__(self) -> None:
        self._buffer.close()

    def _toggle_active(self) -> None:
        self.active = not self.active
        self.toggle = True

    def _update_active(self, pressed_key: int) -> None:
        active = prev_active = self.active
        active ^= (not active) and (pressed_key == pygame.K_SLASH)
        active ^= (active) and (pressed_key == pygame.K_ESCAPE)
        self.active = active
        self.toggled = active != prev_active

    def clear(self) -> None:
        self._buffer.seek(0)
        self._buffer.truncate(0)

    def update(self, pressed_key: int, unicode: str) -> ty.Optional[str]:
        self._update_active(pressed_key)
        if not self.active:
            return
        buffer = self._buffer
        if pressed_key == pygame.K_RETURN:
            self._toggle_active()
            return buffer.getvalue()
        elif pressed_key == pygame.K_BACKSPACE:
            cursor_pos = buffer.tell() - 1
            if cursor_pos < 0:
                return
            buffer.seek(cursor_pos)
            buffer.truncate(cursor_pos)
        else:
            buffer.write(unicode)
        if self.toggled:
            self.clear()

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active:
            return
        screen_width = screen.get_width()
        text_surface = self.font.render(self._buffer.getvalue(), True, self.color)
        text_width = text_surface.get_width()
        width = max(200, text_width + 10)
        self._box.w = width
        self._box.x = screen_width - width - 5
        screen.blit(text_surface, (self._box.x+5, self._box.y+5))
        pygame.draw.rect(screen, self.color, self._box, 2)


class Body:
    __slots__ = "name", "mass", "pos", "vel", "radius", "_color", "orbit", "active"

    def __init__(
        self,
        name: str,
        mass: float,
        pos: complex,
        vel: complex,
        radius: float,
        color: tuple[int, int, int],
    ) -> None:
        self.name = name
        self.pos = pos
        self.vel = vel
        self.radius = radius
        self._color = color
        self.mass = mass
        period = math.tau * math.sqrt(
            pow(abs(pos), 3) / (GRAV_CONST * SOLAR_MASS)
        )
        num_orbit_steps = math.ceil(period / TIMESTEP)
        self.orbit: cl.deque[complex] = cl.deque(maxlen=num_orbit_steps)
        self.active = False

    @property
    def color(self) -> tuple[int, int, int]:
        if self.active:
            return COLOR_WHITE
        return self._color

    def distance_to(self, other: ty.Self) -> float:
        return abs(other.pos - self.pos)

    def attraction_to(self, other: ty.Self) -> complex:
        displacement = other.pos - self.pos
        dist_recip = 1.0 / abs(displacement)
        force_mag = GRAV_CONST * self.mass * other.mass * dist_recip * dist_recip
        return force_mag * (displacement * dist_recip)

    def update_position(self, force: complex) -> None:
        self.vel += force * TIMESTEP / self.mass
        self.pos += self.vel * TIMESTEP
        self.orbit.append(self.pos)

    def update_scale(self, factor: float) -> None:
        self.radius *= factor


def grav_forces(bodies: ty.Sequence[Body]) -> list[complex]:
    forces = [complex(0.0, 0.0)] * len(bodies)
    for (i, body_i), (j, body_j) in it.combinations(enumerate(bodies), 2):
        pairwise_force = body_i.attraction_to(body_j)
        forces[i] += pairwise_force
        forces[j] -= pairwise_force
    return forces


def evolve_bodies(bodies: ty.Sequence[Body]) -> None:
    for body, force in zip(bodies, grav_forces(bodies)):
        body.update_position(force)


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
    scale: float,
    shift: complex,
    half_res: complex,
    show: bool,
    draw_line: bool,
    window: pygame.Surface,
    font: pygame.font.Font,
    color: tuple[int, int, int] = COLOR_WHITE,
    num_segments: int = 360,
) -> None:
    coord = fn.partial(coord_disp, scale=scale, half_res=half_res, shift=shift)
    x, y = coord(body.pos)
    pygame.draw.circle(window, body.color, (x, y), body.radius)
    if draw_line and ((num_points := len(body.orbit)) > 2):
        stride = (num_points // num_segments) + 1
        orbit_points = it.islice(body.orbit, None, num_points - 1, stride)
        orbit_points = it.chain(orbit_points, (body.orbit[-1],))
        traj = tuple(map(coord, orbit_points))
        pygame.draw.aalines(window, body.color, False, traj, 1)
    if (not show) or (body is sun):
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


GameLoop = ty.Iterator[tuple[bool, bool, bool, float, complex, complex]]


def game_loop(
    window: pygame.Surface,
    scale: float,
    bodies: ty.Sequence[Body],
    bg_color: tuple[int, int, int],
    fps: int = 60,
) -> GameLoop:
    clock = pygame.time.Clock()
    scale_factors = {pygame.K_EQUALS: 1.25, pygame.K_MINUS: 0.75}
    rate_factors = {pygame.K_RIGHTBRACKET: 1.25, pygame.K_LEFTBRACKET: 0.75}

    # interface switches:
    run = True
    pause = False
    show_distance = False
    draw_line = True
    active_body = None

    font = pygame.font.SysFont("Trebuchet MS", 21)
    key_key = fn.partial(key_message, window=window, font=font)

    shift = complex(0.0, 0.0)
    display_info = True
    color = pygame.Color('lightskyblue3')
    input_box = TextBox(font, color)

    recentre = False
    while run:
        clock.tick(fps)
        window.fill(bg_color)
        rescale = False
        factor = fps_factor = None
        toggle_fullscreen = False
        for event in pygame.event.get():
            if not run:
                break
            if event.type != pygame.KEYDOWN:
                run = not (event.type == pygame.QUIT)
                continue
            pressed_key, key_char = event.key, event.unicode
            text = input_box.update(pressed_key, key_char)
            if text is not None:
                if active_body is not None:
                    active_body.active = False
                active_body = next(filter(lambda b: b.name.lower() == text.lower(), bodies), None)
                if active_body is not None:
                    active_body.active = True
            if input_box.active:
                continue
            run = not (pressed_key == pygame.K_q)
            pause ^= pressed_key == pygame.K_SPACE
            show_distance ^= pressed_key == pygame.K_d
            draw_line ^= pressed_key == pygame.K_s
            recentre ^= pressed_key == pygame.K_c
            rescale = pressed_key == pygame.K_0
            factor = scale_factors.get(pressed_key, None)
            fps_factor = rate_factors.get(pressed_key, None)
            toggle_fullscreen ^= pressed_key == pygame.K_f
            display_info ^= pressed_key == pygame.K_i
            if not active_body:
                continue
            if key_char == "m":
                active_body.mass *= 0.8
            elif key_char == "M":
                active_body.mass *= 1.2
        if factor:
            scale *= factor
            for body in bodies:
                body.update_scale(factor)
        if fps_factor:
            fps = min(max(10, math.ceil(fps_factor * fps)), 300)
        elif rescale:
            factor = SCALE_PER_AU / (scale * AU)
            scale *= factor
            for body in bodies:
                body.update_scale(factor)
        if toggle_fullscreen:
            pygame.display.toggle_fullscreen()
            toggle_fullscreen = False
        if recentre and active_body:
            shift = -active_body.pos * scale

        disp_info = pygame.display.Info()
        half_res = 0.5 * complex(disp_info.current_w, disp_info.current_h)

        data = pause, show_distance, draw_line, scale, half_res, shift
        yield data  # from ((body, *data) for body in bodies)

        keys = pygame.key.get_pressed()
        distance = 10
        if not input_box.active:
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
        input_box.draw(window)
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


def load_conf(fileobj: io.IOBase):
    data = tomllib.load(fileobj)
    return data


@click.command
@click.option(
    "-r",
    "--resolution",
    nargs=2,
    type=click.IntRange(min=360),
    default=(1280, 720),
)
@click.option(
    "-c",
    "--config",
    type=click.File(mode="rb"),
    default=None,
)
@GameContext("Solar System Simulation")
def main(resolution: tuple[int, int], config: ty.BinaryIO) -> None:
    conf = load_conf(config)

    # pygame program variables:
    window = pygame.display.set_mode(resolution)
    font = pygame.font.SysFont("Trebuchet MS", 16)
    draw_ = fn.partial(draw, window=window, font=font)

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
            mass=props["mass"] * solar_mass,
            pos=rot_op * complex(-props["distance"] * AU, 0.0),
            vel=rot_op * complex(0.0, props["speed"] * unit_speed),
            radius=props["radius"] * AU * scale,
            color=COLOR[name],
        )
        bodies.append(body)
    bodies.sort(key=lambda b: abs(b.pos))
    sun = bodies[0]
    if sun is not next(filter(lambda b: b.name.lower() == "sun", bodies)):
        raise ValueError("Sun is not at the origin.")

    loop = game_loop(window, scale, bodies, fps=100)
    for pause, show, draw_l, scale, half_res, shift in loop:
        for body in bodies:
            draw_(body, sun, scale, shift, half_res, show, draw_l)
        if pause:
            continue
        evolve_bodies(bodies)


if __name__ == "__main__":
    sys.exit(main())
