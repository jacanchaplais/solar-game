import math
import random
import sys
import tomllib
from fractions import Fraction
from pathlib import Path

import click


SCRIPT_DIR = Path(__file__).resolve().parent


def generate_color(min_mag: float) -> tuple[int, int, int]:
    color = [random.randint(1, 256) for _ in range(3)]
    while math.hypot(*color) < min_mag:
        color = [random.randint(1, 255) for _ in range(3)]
    return color


@click.command
@click.argument("num-bodies", type=click.IntRange(2, 128))
@click.argument("output", type=click.File(mode="wt"))
@click.option(
    "-d",
    "--distance",
    type=click.FloatRange(1.0, None),
    default=5.0,
    show_default=True,
)
@click.option(
    "-s",
    "--speed",
    type=click.FloatRange(0.0, None),
    default=5.0E-3,
    show_default=True,
)
def main(num_bodies: int, output, distance: float, speed: float) -> None:
    with open(SCRIPT_DIR / "names.txt", "rt") as f:
        clean_names = (line.strip() for line in f)
        all_names = list(name for name in clean_names if name)
    random.shuffle(all_names)
    names = all_names[:num_bodies]
    names[0] = "sun"
    output.write("bgcolor = [36, 36, 36]\n")
    for idx, name in enumerate(names):
        color = generate_color(200.0)
        angle_frac = Fraction(2, 1) * Fraction(idx, num_bodies)
        output.write(
            f"\n[bodies.{name}]\n"
            "mass = 1.0\n"
            "radius = 2.0E-1\n"
            f"distance = {distance}\n"
            f"speed = {speed}\n"
            f"angle = \'{angle_frac}\'\n"
            f"color = {color}\n"
        )
    
if __name__ == "__main__":
    sys.exit(main())
