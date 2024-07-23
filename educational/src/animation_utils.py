from . import screen

def new_frame(pixel_value = 0):
    frame = [pixel_value] * screen.LED_ROWS
    return frame

def set_pixels(start, end, state, dst = None):
    if dst == None:
        dst = []
    for i in range(start, end + 1):
        dst[i] = state
    
    return dst

def level_to_pixels(level):
    frame = new_frame()
    if level < 0:
        return frame

    set_pixels(0, level, 1, frame)
    return frame
        
def get_level(max_amp):
    if max_amp >= -1.5:
        return 7
    
    if max_amp >= -3:
        return 6
    
    if max_amp >= -6:
        return 5
    
    if max_amp >= -9:
        return 4
    
    if max_amp >= -12:
        return 3
    
    if max_amp >= -15:
        return 2
    
    if max_amp >= -18:
        return 1
    
    if max_amp >= -30:
        return 0
    
    return -1