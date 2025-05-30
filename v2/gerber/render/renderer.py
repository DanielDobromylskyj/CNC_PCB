from PIL import Image, ImageDraw
import math

COLOUR_COPPER = (79, 50, 24)

class InvalidRender(Exception):
    pass


def render_pcb(pcb, is_in_colour: bool=True, scale_size: int=20):
    shape = (math.ceil(pcb.max_xy[0] * scale_size), math.ceil(pcb.max_xy[1] * scale_size))

    if math.inf in shape or -math.inf in shape:
        raise InvalidRender(f"Can't render pcb, min/max positions contain a 'inf'. (You dont have enough memory)")

    base_colour = COLOUR_COPPER if is_in_colour else 1
    view = GerberView(shape, is_in_colour, base_colour, scale_size)

    for layer_name in pcb:
        layer = pcb.get_component(layer_name)
        colour = pcb.get_component_colour(layer_name) if is_in_colour else 0

        view.add_layer(layer, colour)

    return view




class GerberView:
    def __init__(self, shape, in_colour, base_colour, scale_size, offset=None):
        self.shape = shape
        self.in_colour = in_colour
        self.scale = scale_size
        self.offset_x, self.offset_y = offset if offset is not None else (0, 0)

        self.image = Image.new("RGB" if in_colour else "1", (shape[0], shape[1]+4), base_colour)
        self.draw = ImageDraw.Draw(self.image)

    def show(self):
        self.image.show()

    def add_layer(self, layer, colour: int | tuple[int, int, int]):
        if hasattr(layer, "commands"):
            for command in layer.commands:
                if command[0] == "line":
                    x1, y1, x2, y2,width = command[1], command[2], command[3], command[4], command[5]

                    self.draw.line([round((x1+ self.offset_x) * self.scale), self.shape[1] - round((y1+ self.offset_y) * self.scale), round((x2+self.offset_x) * self.scale), self.shape[1] - round((y2+ self.offset_y) * self.scale)], colour, round(width))

                if command[0] == "blit":
                    points = [(round((x+self.offset_x) * self.scale), self.shape[1] - round((y + self.offset_y) * self.scale)) for x, y in command[1]]
                    self.draw.polygon(points, colour)

                if command[0] == "hole":
                    x, y, diameter = command[1:]
                    self.draw.circle([round((x+self.offset_x)*self.scale), self.shape[1] - round((y+ self.offset_y)*self.scale)], round((diameter/2)*self.scale), colour)

