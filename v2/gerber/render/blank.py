from PIL import Image


class GerberView:
    def __init__(self, shape, in_colour, base_colour):
        self.shape = shape
        self.in_colour = in_colour

        self.image = Image.new("RGB" if in_colour else "1", shape, base_colour)

    def show(self):
        self.image.show()