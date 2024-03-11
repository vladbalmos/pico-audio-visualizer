import turtle

# "Led" setup
ROWS = 8
COLS = 10

frame_rate = 60

led_width = 40
led_height = 25
led_spacing_horizontal = 4
led_spacing_vertical = 2
screen_padding = 100

canvas_width = COLS * (led_width + 2 * led_spacing_horizontal) + screen_padding
canvas_height = ROWS * (led_height + 2 * led_spacing_vertical) + screen_padding

bottom_left = (-1 * (canvas_width / 2 - screen_padding / 2 - led_width / 2), 
               -1 * (canvas_height / 2 - screen_padding / 2 - led_height / 2))

# Set up the screen
screen = turtle.Screen()
screen.title('"LED" Audio Visualizer')
screen.bgcolor("black")
screen.setup(width=canvas_width, height=canvas_height)
turtle.tracer(0, 0) # Disable animations until the scene has been initialized


screen.register_shape("led", (
                            (-1 * (led_height / 2), -1 * (led_width / 2)), 
                            (-1 * (led_height / 2), led_width / 2),
                            (led_height / 2, led_width / 2),
                            (led_height / 2, -1 * (led_width / 2))
                         )
)

# Create LED matrixs
led_matrix = []
frames_queue = []

x = bottom_left[0]
y = bottom_left[1]

for col in range(COLS):
    for row in range(ROWS):
        led = turtle.Turtle()
        led.ht()
        
        try:
            led_rows = led_matrix[col]
        except IndexError:
            led_rows = []
            led_matrix.append(led_rows)
            
        led_rows.append(led)
        
        led.shape("led")
        led.penup()
        
        if row < 5:
            led.color("green")
        elif row < 7:
            led.color("yellow")
        else:
            led.color("red")

        led.speed(0)
        led.goto(x, y)
        
        y += led_height + 2 * led_spacing_vertical

    x += led_width + 2 * led_spacing_horizontal
    y = bottom_left[1]
        
turtle.tracer(1) # Re-enable animations
        
def set_framerate(fps):
    global frame_rate
    frame_rate = fps

def run():
    try:
        led_state = frames_queue.pop()
    except:
        return

    for i in range(0, COLS):
        for j in range(0, ROWS):
            led = led_matrix[i][j]
            try:
                state = led_state[i][j]
            except:
                continue
            
            if state == 0 and led.isvisible():
                led.ht()
                continue
            
            if state == 1 and not led.isvisible():
                led.st()
                continue
            
    next_frame = 1000 / frame_rate
    screen.ontimer(run, next_frame)