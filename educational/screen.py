import time
import pygame
import sys
from collections import deque

LED_ROWS = 8
LED_COLS = 10
SCREEN_PADDING = 100

screen = None
clock = None
framerate = None

# Colors
black = (0, 0, 0)
yellow = (255, 255, 0)
green = (0, 255, 0)
red = (255, 0, 0)

led_matrix = []
raster_queue = deque()

class Led():
    WIDTH = 40
    HEIGHT = 25
    SPACING_HORIZONTAL = 4
    SPACING_VERTICAL = 2

    def __init__(self, x, y, color, visible = True):
        self.x = x
        self.y = y
        self.color = color
        self.visible = visible
        
    def render(self):
        if not self.visible:
            return
        pygame.draw.rect(screen, self.color, (self.x, self.y, Led.WIDTH, Led.HEIGHT))
            

def init(animation_framerate):
    global screen, clock, led_matrix, framerate

    framerate = animation_framerate

    # Screen dimensions
    screen_width = LED_COLS * (Led.WIDTH + 2 * Led.SPACING_HORIZONTAL) + SCREEN_PADDING
    screen_height = LED_ROWS * (Led.HEIGHT + 2 * Led.SPACING_VERTICAL) + SCREEN_PADDING

    bottom_left = (SCREEN_PADDING / 2 + Led.SPACING_HORIZONTAL, screen_height - (SCREEN_PADDING / 2) + Led.SPACING_VERTICAL)

    # Setup the display
    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption('"LED" Audio Visualizer')

    # Clock to control the frame rate
    clock = pygame.time.Clock()

    x = bottom_left[0]
    y = bottom_left[1]

    for col in range(LED_COLS):
        for row in range(LED_ROWS):

            try:
                led_rows = led_matrix[col]
            except IndexError:
                led_rows = []
                led_matrix.append(led_rows)
                
            if row < 5:
                color = green
            elif row < 7:
                color = yellow
            else:
                color = red

            led = Led(x, y, color, True)
            led_rows.append(led)

            y -= Led.HEIGHT + 2 * Led.SPACING_VERTICAL

        x += Led.WIDTH + 2 * Led.SPACING_HORIZONTAL
        y = bottom_left[1]
        
def mainloop(callback):
    # Main game loop
    running = True
    last_run = 0
    while running:
        now = time.time()
        # print((now - last_run) * 1000)
        last_run = now

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        callback(raster_queue)
        
        try:
            pixels = raster_queue.popleft()
        except:
            clock.tick(framerate)
            continue
            
        # Clear the screen
        screen.fill(black)

        # Draw the leds
        for i in range(0, LED_COLS):
            for j in range(0, LED_ROWS):
                led_state = pixels[i][j]
                led = led_matrix[i][j]
                led.visible = led_state
                led.render()

        # Update the display
        pygame.display.flip()

        # Cap the frame rate at 60 frames per second
        clock.tick(framerate)

    # Quit Pygame
    pygame.quit()
    sys.exit()
    
if __name__ == '__main__':
    init()
    start()