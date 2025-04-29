from .settings import Settings
from .gcode import CNC_Gcode

import math


def create_divots(pcb, settings):
    gcode = CNC_Gcode(settings)

    hole_layers = ["Vias", "NoPlateThoughHole", "PlatedThoughHole"]
    height = pcb.max_xy[1] - pcb.min_xy[1]

    for layer_name in pcb:
        layer = pcb.get_component(layer_name)

        if layer_name in hole_layers:
            for command in layer.commands:
                if command[0] == "hole":
                    x, y, diameter = command[1:]

                    x, y = x * settings.scale, (height - y) * settings.scale

                    gcode.go_to(x, y, settings.travel_height)

                    gcode.spin()
                    gcode.cut_to(x, y, -0.1)
                    gcode.stop()

                    gcode.go_to(x, y,  settings.travel_height)

    return gcode.gcode


def cut_circle(gcode, x, y, z, r, res=20):
    delta_angle = math.radians(360) / res

    for i in range(res):
        angle = delta_angle * i
        dx, dy = math.cos(angle) * r, math.sin(angle) * r

        gcode.cut_to(x + dx, y + dy, z)



def create_gcode_from_layer(gcode, height, layer, settings: Settings):
    drill_radius_half = settings.drill_tool_width / 4
    for command in layer.commands:
        if command[0] == "hole":
            x, y, diameter = command[1:]

            x, y = x * settings.scale, (height-y-drill_radius_half) * settings.scale

            if diameter <= settings.drill_tool_width:
                if diameter < settings.drill_tool_width:
                    print("[WARNING] Though hole / drill tool too large for hole")

                gcode.go_to(x, y, settings.travel_height)

                gcode.spin()
                gcode.go_to(x, y, 1)

                for i in range(0, math.floor(settings.cut_though_height), -1):
                    gcode.cut_to(x, y, i)
                    gcode.go_to(x, y, 1)


                gcode.stop()
                gcode.go_to(x, y, settings.travel_height)

            else:
                gcode.go_to(x, y, settings.travel_height)

                gcode.spin()
                gcode.go_to(x, y, 1)

                for h in range(0, math.floor(settings.cut_though_height), -1):
                    for sub_radius in range(0, math.floor(((diameter-settings.drill_tool_width)*settings.scale)/2), math.floor((settings.drill_tool_width * settings.scale)/2)):
                        cut_circle(gcode, x, y, h, sub_radius)

                    cut_circle(gcode, x, y, h, (diameter*settings.scale-settings.drill_tool_width)/2)

                gcode.stop()
                gcode.go_to(x, y, settings.travel_height)


def create_gcode_from_pcb(pcb, settings: Settings):
    gcode = CNC_Gcode(settings)
    height = pcb.max_xy[1] - pcb.min_xy[1]

    hole_layers = ["Vias", "NoPlateThoughHole", "PlatedThoughHole"]

    for layer_name in pcb:
        layer = pcb.get_component(layer_name)

        if layer_name in hole_layers:
            create_gcode_from_layer(gcode, height, layer, settings)

    return gcode.gcode


