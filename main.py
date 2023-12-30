import contextlib as ctx
import typing as ty
from math import pi

import pygame


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


def game_loop(screen: pygame.Surface, fps: int = 60):
    done = False
    clock = pygame.time.Clock()

    counter = 0
    while not done:
        # This limits the while loop to a max of 60 times per second.
        # Leave this out and we will use all CPU we can.
        clock.tick(fps)
        counter += 1

        for event in pygame.event.get():  # User did something
            if event.type == pygame.QUIT:  # If user clicked close
                done = True  # Flag that we are done so we exit this loop
        
        # Clear the screen and set the screen background
        screen.fill("white")

        yield counter

        # Go ahead and update the screen with what we've drawn.
        # This MUST happen after all the other drawing commands.
        pygame.display.flip()


@GameContext("Example code for the draw module")
def main() -> None:
    # Set the height and width of the screen
    screen = pygame.display.set_mode(size=[400, 300])
    
    for _ in game_loop(screen):
        # Draw on the screen a green line from (0, 50) to (50, 80)
        # Because it is an antialiased line, it is 1 pixel wide.
        # Uses (r, g, b) color - medium sea green.
        pygame.draw.aaline(screen, (60, 179, 113), [0, 50], [50, 80], True)

        # Draw on the screen 3 black lines, each 5 pixels wide.
        # The 'False' means the first and last points are not connected.
        pygame.draw.aalines(
            screen, "black", False, [[0, 80], [50, 90], [200, 80], [220, 30]], 5
        )

        # # Draw a rectangle outline
        # pygame.draw.rect(screen, "black", [75, 10, 50, 20], 2)
        #
        # # Draw a solid rectangle. Same color as "black" above, specified in a new way
        # pygame.draw.rect(screen, (0, 0, 0), [150, 10, 50, 20])
        #
        # # Draw a rectangle with rounded corners
        # pygame.draw.rect(screen, "green", [115, 210, 70, 40], 10, border_radius=15)
        # pygame.draw.rect(
        #     screen,
        #     "red",
        #     [135, 260, 50, 30],
        #     0,
        #     border_radius=10,
        #     border_top_left_radius=0,
        #     border_bottom_right_radius=15,
        # )
        #
        # # Draw an ellipse outline, using a rectangle as the outside boundaries
        # pygame.draw.ellipse(screen, "red", [225, 10, 50, 20], 2)
        #
        # # Draw an solid ellipse, using a rectangle as the outside boundaries
        # pygame.draw.ellipse(screen, "red", [300, 10, 50, 20])
        #
        # # This draws a triangle using the polygon command
        # pygame.draw.polygon(screen, "black", [[100, 100], [0, 200], [200, 200]], 5)
        #
        # # Draw an arc as part of an ellipse.
        # # Use radians to determine what angle to draw.
        # pygame.draw.arc(screen, "black", [210, 75, 150, 125], 0, pi / 2, 2)
        # pygame.draw.arc(screen, "green", [210, 75, 150, 125], pi / 2, pi, 2)
        # pygame.draw.arc(screen, "blue", [210, 75, 150, 125], pi, 3 * pi / 2, 2)
        # pygame.draw.arc(screen, "red", [210, 75, 150, 125], 3 * pi / 2, 2 * pi, 2)
        #
        # # Draw a circle
        # pygame.draw.circle(screen, "blue", [60, 250], 40)
        #
        # # Draw only one circle quadrant
        # pygame.draw.circle(screen, "blue", [250, 250], 40, 0, draw_top_right=True)
        # pygame.draw.circle(screen, "red", [250, 250], 40, 30, draw_top_left=True)
        # pygame.draw.circle(screen, "green", [250, 250], 40, 20, draw_bottom_left=True)
        # pygame.draw.circle(screen, "black", [250, 250], 40, 10, draw_bottom_right=True)


if __name__ == "__main__":
    main()
