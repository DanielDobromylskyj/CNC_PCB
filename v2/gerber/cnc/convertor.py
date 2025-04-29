from .gerber_to_image import convert_gerber_to_image
from .gpu_path_generator import create_outline
from .image_to_toolpath import image_to_tool_path
from .drill_holes import create_gcode_from_pcb as drill_holes_to_path
from .drill_holes import create_divots
from .gcode import create_header as create_gcode_header
from .settings import Settings

import math
import os


def convert(pcb, settings: Settings, output_path: str="/"):
    gcode_header = create_gcode_header(pcb, settings)

    top_view, bottom_view = convert_gerber_to_image(pcb, settings)

    top_view_outline = create_outline(top_view, round(settings.cutting_tool_width * settings.scale))
    bottom_view_outline = create_outline(bottom_view, round(settings.cutting_tool_width * settings.scale))

    top_tool_path = image_to_tool_path(top_view_outline, settings)
    bottom_tool_path = image_to_tool_path(bottom_view_outline, settings)

    if settings.create_drill_dimples is True:
        top_tool_path += create_divots(pcb, settings)

    though_hole_path = drill_holes_to_path(pcb, settings)

    top_tool_path = top_tool_path.replace("FILE_TOTAL_LINE_COUNT", str(len(top_tool_path.split("\n")))).replace("ESTIMATED_TIME", "1")
    bottom_tool_path = bottom_tool_path.replace("FILE_TOTAL_LINE_COUNT", str(len(bottom_tool_path.split("\n")))).replace("ESTIMATED_TIME", "1")
    though_hole_path = though_hole_path.replace("FILE_TOTAL_LINE_COUNT", str(len(though_hole_path.split("\n")))).replace("ESTIMATED_TIME", "1")

    with open(os.path.join(output_path, "TopLayer.cnc"), "w") as f:
        f.write(gcode_header + top_tool_path)

    with open(os.path.join(output_path, "BottomLayer.cnc"), "w") as f:
        f.write(gcode_header + bottom_tool_path)

    with open(os.path.join(output_path, "ThoughHoles.cnc"), "w") as f:
        f.write(gcode_header + though_hole_path)
    
