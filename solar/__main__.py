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
COLOR_WHITE = COLOR["white"]

SCALE_PER_AU = 200.0


class Body:
    __slots__ = (
        "name",
        "pos",
        "vel",
        "radius",
        "color",
        "mass",
        "orbit",
        "sun",
        "distance_to_sun",
    )

    def __init__(self, name, x, y, vel_x, vel_y, radius, color, mass):
        self.name = name
        self.pos = complex(x, y)
        self.vel = complex(vel_x, vel_y)
        self.radius = radius
        self.color = color
        self.mass = mass
        period = math.tau * math.sqrt(
            pow(abs(x), 3) / (GRAV_CONST * SOLAR_MASS)
        )
        self.orbit = cl.deque(maxlen=int(period // TIMESTEP))
        self.sun = False
        self.distance_to_sun = 0.0

    @property
    def x_vel(self) -> float:
        return self.vel.real

    @property
    def y_vel(self) -> float:
        return self.vel.imag

    def attraction(self, other):
        displacement = other.pos - self.pos
        distance, theta = cmath.polar(displacement)
        if other.sun:
            self.distance_to_sun = distance
        force = GRAV_CONST * self.mass * other.mass / (distance * distance)
        force = cmath.rect(force, theta)
        return force

    def update_position(self, planets):
        total_force = complex(0.0, 0.0)
        for planet in filter(fn.partial(op.is_not, self), planets):
            total_force += self.attraction(planet)
        self.vel += total_force * TIMESTEP / self.mass
        self.pos += self.vel * TIMESTEP
        self.orbit.append((self.pos.real, self.pos.imag))

    def update_scale(self, scale):
        self.radius *= scale


def coord_disp(
    x: float,
    y: float,
    scale: float,
    move_x: float = 0.0,
    move_y: float = 0.0
) -> tuple[float, float]:
    half_width = 0.5 * pygame.display.Info().current_w
    half_height = 0.5 * pygame.display.Info().current_h
    return (x * scale + half_width + move_x, y * scale + half_height + move_y)



def draw(
    body: Body,
    window: pygame.Surface,
    scale: float,
    show: bool,
    move_x: float,
    move_y: float,
    draw_line: bool,
    display_dist: bool,
    font: pygame.font.Font,
) -> None:
    coord_ = fn.partial(coord_disp, scale=scale, move_x=move_x, move_y=move_y)
    x, y = coord_(body.pos.real, body.pos.imag)
    pygame.draw.circle(
        window, body.color, (x, y), body.radius
    )
    traj = tuple(it.starmap(coord_, body.orbit))
    if draw_line and (len(body.orbit) > 2):
        pygame.draw.lines(window, body.color, False, traj, 1)
    if not (display_dist and show):
        return
    distance_text = font.render(
        f"{round(body.distance_to_sun * 1.057 * 10 ** -16, 8)} "
        "light years",
        True,
        COLOR_WHITE,
    )
    window.blit(
        distance_text,
        (
            x - 0.5 * distance_text.get_width(),
            y - 0.5 * distance_text.get_height() - 20.0,
        ),
    )


class PygameContext(ctx.ContextDecorator):
    def __enter__(self: ty.Self) -> ty.Self:
        pygame.init()
        pygame.display.set_caption("Solar System Simulation")
        return self

    def __exit__(self, *_) -> ty.Literal[False]:
        pygame.quit()
        return False


@PygameContext()
def main(conf) -> None:
    # pygame program variables:
    clock = pygame.time.Clock()
    window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    font_1 = pygame.font.SysFont("Trebuchet MS", 21)
    font_2 = pygame.font.SysFont("Trebuchet MS", 16)

    # interface switches:
    run = True
    pause = False
    show_distance = False
    draw_line = True

    # constants and units:
    color_universe = COLOR["universe"]
    scale = SCALE_PER_AU / AU
    unit_speed = AU / CONST["SECONDS_PER_DAY"]
    solar_mass = CONST["SOLAR_MASS"]
    scale_factors = (1.25, 0.75)

    # populating and sorting the bodies from the config file:
    planets = []
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
        planets.append(body)
    planets.sort(key=lambda b: abs(b.pos))
    sun = planets[0]
    sun.sun = True

    move_x = move_y = 0.0
    while run:
        clock.tick(60)
        window.fill(color_universe)

        for event in pygame.event.get():
            event_type = event.type
            run = not (event_type == pygame.QUIT)
            if event_type == pygame.KEYDOWN:
                pressed_key = event.key
                run &= not (
                    (pressed_key == pygame.K_x)
                    or (pressed_key == pygame.K_ESCAPE)
                )
                pause ^= pressed_key == pygame.K_SPACE
                show_distance ^= pressed_key == pygame.K_d
                draw_line ^= pressed_key == pygame.K_s
                if pressed_key == pygame.K_c:
                    move_x, move_y = (
                        -sun.pos.real * scale,
                        -sun.pos.imag * scale,
                    )
            elif (event_type == pygame.MOUSEBUTTONDOWN) and (
                event.button in {4, 5}
            ):
                factor = scale_factors[event.button - 4]
                scale *= factor
                for planet in planets:
                    planet.update_scale(factor)
            if not run:
                break

        keys = pygame.key.get_pressed()
        mouse_x, mouse_y = pygame.mouse.get_pos()
        window_w, window_h = pygame.display.get_surface().get_size()
        distance = 10
        if keys[pygame.K_LEFT] or mouse_x == 0:
            move_x += distance
        if keys[pygame.K_RIGHT] or mouse_x == window_w - 1:
            move_x -= distance
        if keys[pygame.K_UP] or mouse_y == 0:
            move_y += distance
        if keys[pygame.K_DOWN] or mouse_y == window_h - 1:
            move_y -= distance

        for plan_num, planet in enumerate(planets):
            not_sol = plan_num != 0
            draw(planet, window, scale, show_distance, move_x, move_y, draw_line, not_sol, font_2)
            planet_surface = font_1.render(
                f"- {planet.name.capitalize()}", True, planet.color
            )
            window.blit(planet_surface, (15, (285 + (plan_num * 30))))
            if pause:
                continue
            planet.update_position(planets)

        fps_text = font_1.render(
            "FPS: " + str(int(clock.get_fps())), True, COLOR_WHITE
        )
        window.blit(fps_text, (15, 15))
        text_surface = font_1.render(
            "Press X or ESC to exit", True, COLOR_WHITE
        )
        window.blit(text_surface, (15, 45))
        text_surface = font_1.render(
            "Press D to turn on/off distance", True, COLOR_WHITE
        )
        window.blit(text_surface, (15, 75))
        text_surface = font_1.render(
            "Press S to turn on/off drawing orbit lines", True, COLOR_WHITE
        )
        window.blit(text_surface, (15, 105))
        text_surface = font_1.render(
            "Use mouse or arrow keys to move around", True, COLOR_WHITE
        )
        window.blit(text_surface, (15, 135))
        text_surface = font_1.render("Press C to center", True, COLOR_WHITE)
        window.blit(text_surface, (15, 165))
        text_surface = font_1.render(
            "Press Space to pause/unpause", True, COLOR_WHITE
        )
        window.blit(text_surface, (15, 195))
        text_surface = font_1.render(
            "Use scroll-wheel to zoom", True, COLOR_WHITE
        )
        window.blit(text_surface, (15, 225))
        pygame.display.update()


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    config_path = script_dir / "../config.toml"
    with open(config_path, "rb") as f:
        conf = load_conf(f)
    sys.exit(main(conf))
