from .settings import Settings
from ..render import renderer, blank

import math

def convert_gerber_to_image(pcb, settings: Settings):
    if math.inf in pcb.max_xy or math.inf in pcb.min_xy or -math.inf in pcb.max_xy or -math.inf in pcb.min_xy:
        raise Exception(f"Can't convert pcb, min/max positions contain a 'inf'. (You dont have enough memory)")

    outline = pcb.get_component("Outline")
    offset = (-outline.min_xy[0], -outline.min_xy[1])

    shape = (math.ceil((outline.max_xy[0] - outline.min_xy[0]) * settings.scale), math.ceil((outline.max_xy[1] - outline.min_xy[1]) * settings.scale))

    view_top = renderer.GerberView(shape, False, 1, settings.scale, offset)
    view_bottom = renderer.GerberView(shape, False, 1, settings.scale, offset)

    top_layers = ["TopLayer"]
    bottom_layers = ["BottomLayer"]

    for layer_name in pcb:
        layer = pcb.get_component(layer_name)

        if layer_name in top_layers:
            view_top.add_layer(layer, 0)

        if layer_name in bottom_layers:
            view_bottom.add_layer(layer, 0)

    view_top.show()
    return view_top.image, view_bottom.image

