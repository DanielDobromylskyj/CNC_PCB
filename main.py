from matplotlib.patches import Polygon
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
import copy
import json
import math
import os
import re

from convert import convert_image_to_gcode
from logger import ProgressLogger

from gpu_path_generator import create_outline as gpu_create_outline

def read_coord(data, int_count, float_count):  # todo - make this have diff values for x/y
    x_data, other = data.replace("X", "").split("Y")
    y_data = ""

    for i in range(int_count + float_count + 1):  # expect a possible "-"
        if other[i].isdigit() or other[i] == "-":
            y_data += other[i]
        else:
            break


    return float(f"{x_data[:-float_count]}.{x_data[-float_count:]}"), float(f"{y_data[:-float_count]}.{y_data[-float_count:]}")


def smart_reader(data):
    output = {}

    started_reading_number = False
    current_value = ""
    current_name = ""

    for char in list(data):
        if char in "0123456789-":
            started_reading_number = True
            current_value += char

        else:
            if started_reading_number:
                started_reading_number = False

                if len(current_value) == 10:
                    output[current_name] = current_value

                elif len(current_value) > 3:
                    output[current_name] = int(current_value) / 100000
                else:
                    output[current_name] = int(current_value)

                current_value = ""
                current_name = char
            else:
                current_name += char

    if current_name != "" and current_value != "":
        if len(current_value) == 10:
            output[current_name] = current_value

        elif len(current_value) > 3:
            output[current_name] = int(current_value) / 100000
        else:
            output[current_name] = int(current_value)

    return output



def read_arc(data, int_count, float_count):
    x_data, other = data.replace("X", "").split("Y")
    y_data, other = other.split("I")
    i_data, other = other.split("J")
    j_data, d_data = other.split("D")

    return (
        float(f"{x_data[:-float_count]}.{x_data[-float_count:]}"),
        float(f"{y_data[:-float_count]}.{y_data[-float_count:]}"),
        float(f"{i_data[:-float_count]}.{i_data[-float_count:]}"),
        float(f"{j_data[:-float_count]}.{j_data[-float_count:]}"),
        int(d_data),
    )


DEFAULT_DRAW_SHAPES = {
                "C": {
                    "primitive": "circle",
                    "params": ["1", "$1"]
                },

                "R": {
                    "primitive": "rect",
                    "params": ["1", "$1", "$2"]
                }
            }

class Drill_Gerber:
    def __init__(self, path, bodge_scale_factor=1):
        self.holes = []
        self.bodge_scale_factor = bodge_scale_factor

        self.__parse(path)

    def __parse(self, path):
        hole_sizes = {}
        current_hole_size = None

        drill_position_mode = None
        using_metric_no_leading_zeros = False

        if not os.path.exists(path):
            return

        with open(path, 'r') as f:
            lines = f.read().split("\n")

        for line in lines:
            line = line.strip()

            if line.startswith(';'):
                continue

            if line == "METRIC,LZ,000.000":
                using_metric_no_leading_zeros = True

            if line == "G90":
                drill_position_mode = "abs"

            if line == "G91":
                drill_position_mode = "rel"

            if line.startswith('T'):
                index = line[1:3]

                if len(line) > 3 and line[3] == "C":
                    size = float(line.split("C")[1])
                    hole_sizes[index] = size / 2

                else:
                    current_hole_size = hole_sizes[index]

            if line == "%":  # Setup finished, ensure we have everything we need
                if using_metric_no_leading_zeros is False:
                    raise NotImplementedError("File is not using metric/mm OR no leading zeros, Or Unsupported value storage (expected XXX.YYY in form XXXYYY)")

            if line == "M30":
                return  # END OF FILE

            if line.startswith('X'):
                x_pos_data, y_pos_data = line[1:].split("Y")

                x_pos = float(x_pos_data[:3] + "." + x_pos_data[3:]) * self.bodge_scale_factor
                y_pos = float(y_pos_data[:3] + "." + y_pos_data[3:]) * self.bodge_scale_factor

                if drill_position_mode == "abs":
                    self.holes.append((x_pos, y_pos, current_hole_size))

                elif drill_position_mode == "rel":
                    prev_hole = self.holes[-1]
                    self.holes.append((x_pos + prev_hole[0], y_pos + prev_hole[1], current_hole_size))
                else:
                    raise Exception("Drill position mode not defined (abs / rel)")


class Mask_Gerber:
    def __init__(self, path):
        self.pad_locations = []
        self.pad_definitions = {}
        self.pad_shapes = {}

        self.__parse(path)

    def __parse(self, path):
        if not os.path.exists(path):
            return

        with open(path, 'r') as f:
            gerber_data = f.read()

            pad_shapes = copy.deepcopy(DEFAULT_DRAW_SHAPES)
            pad_definitions = {}
            pad_locations = []
            current_definition_code = None

            x_int_digits = 0
            x_float_digits = 0

            y_int_digits = 0
            y_float_digits = 0
            # Split the data by lines
            lines = gerber_data.split('\n')

            # Parse pad definitions (%ADD) and store them in the dictionary
            for line in lines:
                # %AMMACRO1*21,1,$1,$2,0,0,$3*%
                # %ADD10MACRO1,2.4702X1.5049X0.0000*%

                if line.startswith("%AM"):
                    pad_shape = line.split("*")[0][3:]
                    chunks = line.split("*")[1].split(",")

                    pad_shapes[pad_shape] = {
                        "primitive": chunks[0],
                        "params": chunks[1:]
                    }

                if line.startswith('%ADD'):
                    pad_num = line[4:6]

                    chunks = line.split("*")[0].split(",")

                    # Store the pad definition with pad number as the key
                    pad_definitions[pad_num] = {
                        "shape": chunks[0][len("%ADDXY"):],
                        "params": chunks[1].split("X") if len(chunks) > 1 else []
                    }

            # Parse pad locations (X, Y positions) and associate them with pad shapes
            loading = True

            for line in lines:
                if line.startswith("%FS"):
                    if not line.startswith("%FSLA"):
                        raise NotImplementedError("No way of dealing with Leading zeros / Non absolute coords at this time")

                    x_int_digits = int(line[6])
                    x_float_digits = int(line[7])

                    y_int_digits = int(line[9])
                    y_float_digits = int(line[10])

                if line.startswith("D"):
                    code = line[1:3]
                    if code in pad_definitions:
                        current_definition_code = code

                if line == "%LPD*%":
                    loading = False
                    continue

                # Ignore G01 Since we don't care about moving anything in this format
                if line.startswith("X") and not loading:
                    x_pos, y_pos = read_coord(line, x_int_digits, x_float_digits)

                    if line.endswith("D03*"):  # blit
                        pad_locations.append({
                            "pos": (x_pos, y_pos),
                            "shape": current_definition_code
                        })


            self.pad_locations = pad_locations
            self.pad_definitions = pad_definitions
            self.pad_shapes = pad_shapes


class Gerber:
    def __init__(self, path):
        self.commands = None
        self.apertures = None

        self.__parse_gerber(path)

    def __parse_gerber(self, filename):
        """Parse Gerber .GKO file, extract drawing commands and trace widths."""
        self.commands = []
        self.apertures = {}  # Stores aperture sizes (e.g., {10: 0.254, 15: 0.0115})
        active_aperture = None
        x, y = None, None  # Track last position

        pad_shapes = copy.deepcopy(DEFAULT_DRAW_SHAPES)
        pad_definitions = {}
        current_definition_code = None

        draw_mode = 0

        with open(filename, 'r') as file:
            for raw_line in file:  # todo - Re implement without regex
                line = raw_line.strip()
                if '*' in line:
                    line = line.split('*')[0]  # Remove trailing '*'

                # Match aperture definitions (e.g., %ADD10C,0.2540*%)
                aperture_match = re.match(r'%ADD(\d+)C,([\d.]+)', line)
                if aperture_match:
                    aperture_num = int(aperture_match.group(1))
                    aperture_size = float(aperture_match.group(2))
                    self.apertures[aperture_num] = aperture_size


                if line.startswith("%AM"):
                    pad_shape = raw_line.split("*")[0][3:]

                    chunks = raw_line.split("*")[1].split(",")

                    pad_shapes[pad_shape] = {
                        "primitive": chunks[0],
                        "params": chunks[1:]
                    }

                if raw_line.startswith('%ADD'):
                    pad_num = line[4:6]

                    chunks = line.split("*")[0].split(",")

                    # Store the pad definition with pad number as the key
                    pad_definitions[pad_num] = {
                        "shape": chunks[0][len("%ADDXY"):],
                        "params": chunks[1].split("X") if len(chunks) > 1 else []
                    }


                if line.startswith("D"):
                    code = line[1:3]

                    if code in pad_definitions:
                        current_definition_code = code

                values = smart_reader(line)

                if values:
                    if "G" in values:
                        if values["G"] == 4:
                            continue # comment

                        draw_mode = values["G"]

                    if "X" in values and "Y" in values:
                        d_mode = values["D"] if "D" in values else -1

                        width = self.apertures.get(active_aperture, 0.2)  # fix me

                        if draw_mode == 1:
                            if d_mode == 2:
                                self.commands.append(('move', values["X"], values["Y"]))

                            elif d_mode == 1:
                                self.commands.append(('draw',  x, y, values["X"], values["Y"], width))

                            elif d_mode == 3:
                                x, y = values["X"], values["Y"]
                                definition = pad_definitions[current_definition_code]

                                if current_definition_code in pad_shapes:
                                    shape = pad_shapes[current_definition_code]
                                else:
                                    shape = pad_shapes[definition["shape"]]

                                points = PCB.convert_shape_to_lines(shape, definition["params"])
                                points = [((x + px), (y + py)) for px, py in points]

                                ox, oy = points[0]
                                self.commands.append(('move', ox, oy))

                                for point in points:
                                    self.commands.append(('draw',  ox, oy, point[0], point[1], width))
                                    ox, oy = point




                            x, y = values["X"], values["Y"]

                        elif draw_mode == 2:  # arc
                            i, j, d = values["I"], values["J"], values["D"]

                            start_x = x
                            start_y = y

                            center_x = start_x + i
                            center_y = start_y + j

                            radius = math.sqrt(i ** 2 + j ** 2)

                            start_angle = math.atan2(start_y - center_y, start_x - center_x)
                            end_angle = math.atan2(values["Y"] - center_y, values["X"] - center_x)

                            if end_angle >= start_angle:
                                end_angle -= 2 * math.pi

                            angle_step = (end_angle - start_angle) / 20

                            # Generate the points along the arc using list comprehension
                            arc_points = [(center_x + radius * math.cos(start_angle + i * angle_step),
                                           center_y + radius * math.sin(start_angle + i * angle_step))
                                          for i in range(20 + 1)]

                            x, y = arc_points[-1]
                            for i, point in enumerate(arc_points[1:]):
                                self.commands.append(
                                    ('draw', point[0], point[1], arc_points[i][0], arc_points[i][1], width))

                        elif draw_mode == 3:  # arc
                            i, j, d = values["I"], values["J"], values["D"]

                            start_x = x
                            start_y = y

                            center_x = start_x + i
                            center_y = start_y + j

                            radius = math.sqrt(i ** 2 + j ** 2)

                            start_angle = math.atan2(start_y - center_y, start_x - center_x)
                            end_angle = math.atan2(values["Y"] - center_y, values["X"] - center_x)


                            if end_angle <= start_angle:
                                end_angle += 2 * math.pi

                            angle_step = (end_angle - start_angle) / 20

                            # Generate the points along the arc using list comprehension
                            arc_points = [(center_x + radius * math.cos(start_angle + i * angle_step),
                                           center_y + radius * math.sin(start_angle + i * angle_step))
                                          for i in range(20 + 1)]

                            x, y = arc_points[-1]
                            for i, point in enumerate(arc_points[1:]):
                                self.commands.append(
                                    ('draw', point[0], point[1], arc_points[i][0], arc_points[i][1], width))

                        else:
                            x, y = values["X"], values["Y"]




class PCB:
    def __init__(self, path_to_extracted_gerber):
        self.version = "0.3"
        self.path = path_to_extracted_gerber

        self.outline = Gerber(os.path.join(self.path, "Gerber_BoardOutlineLayer.GKO"))

        self.topLayer = Gerber(os.path.join(self.path, "Gerber_TopLayer.GTL"))
        self.topSilkscreen = Gerber(os.path.join(self.path, "Gerber_TopSilkscreenLayer.GTO"))
        self.topPasteMask = Mask_Gerber(os.path.join(self.path, "Gerber_TopPasteMaskLayer.GTP"))
        self.topSolderMask = Mask_Gerber(os.path.join(self.path, "Gerber_TopSolderMaskLayer.GTS"))

        self.bottomLayer = Gerber(os.path.join(self.path, "Gerber_BottomLayer.GBL"))

        self.vias = Drill_Gerber(os.path.join(self.path, "Drill_PTH_Through_Via.DRL"))
        self.no_plated_though_holes = Drill_Gerber(os.path.join(self.path, "Drill_NPTH_Through.DRL"))
        self.plated_though_holes = Drill_Gerber(os.path.join(self.path, "Drill_PTH_Through.DRL"))

        outline_points: list[tuple[float, float]] = [(command[1], command[2]) for command in self.outline.commands if
                                                     command[0] == "draw"]
        min_xy = min(outline_points, key=lambda p: p[0])[0] - 1, min(outline_points, key=lambda p: p[1])[1] - 1
        max_xy = max(outline_points, key=lambda p: p[0])[0] + 1, max(outline_points, key=lambda p: p[1])[1] + 1

        self.size = [max_xy[0] - min_xy[0], max_xy[1] - min_xy[1]]

    @staticmethod
    def convert_shape_to_lines(shape, def_params):
        params = []
        for i, param in enumerate(shape["params"]):
            if param.startswith("$"):
                if int(param[1:]) > len(def_params):
                    raise IndexError("Too little params when converting shape to lines")
                params.append(float(def_params[int(param[1:]) - 1]))
            else:
                params.append(float(param))

        if shape["primitive"] == '21':
            visible, width, height, cx, cy, r = params
            r = 0.1

            if visible == 1:
                return [
                    (
                        cx - (width / 2) + r,
                        cy - (height / 2),
                    ),
                    (
                        cx + (width / 2) - r,
                        cy - (height / 2),
                    ),
                    (
                        cx + (width / 2),
                        cy - (height / 2) + r,
                    ),
                    (
                        cx + (width / 2),
                        cy + (height / 2) - r,
                    ),
                    (
                        cx + (width / 2) - r,
                        cy + (height / 2),
                    ),
                    (
                        cx - (width / 2) + r,
                        cy + (height / 2),
                    ),
                    (
                        cx - width / 2,
                        cy + (height / 2) - r,
                    ),
                    (
                        cx - width / 2,
                        cy - (height / 2) + r,
                    )
                ]

        elif shape["primitive"] == "circle":
            visible, width = params

            if visible == 1:
                r = width / 2
                return [(r*math.cos(a), r*math.sin(a)) for a in [i*(2*math.pi/50) for i in range(50)]]

        elif shape["primitive"] == "rect":
            return PCB.convert_shape_to_lines({"primitive": "21", "params": ["1", "$1", "$2", "0", "0", "0"]}, params)

        elif shape["primitive"] == "4":
            visible, vert_count = params[:2]

            if visible == 1:
                vertices = params[2:2+((int(vert_count)+1)*2)]
                rotation = params[-1]

                if rotation != 0:
                    raise NotImplementedError("Rotation of a primitive (4) is not yet supported")

                return [(vertices[vertex_index*2], vertices[(vertex_index*2) + 1]) for vertex_index in range(int(vert_count))]

        else:
            raise NotImplementedError(f"Unknown Primitive '{shape['primitive']}'")

        return []

    @staticmethod
    def default_settings():
        return {
            "tool_head": "levelTwoCNCToolheadForSM2",
            "machine": "A400",
            "max_power": 255,
            "work_speed(mm/min)": 60,
            "jog_speed(mm/min)": 1500,
            "power (%)": 0,
            "max_tool_width_at_4mm": 1,
            "hole_tool_width": 1,

            "pcb_hole_outline_width": 0.2,

            "separate_drill_gcode": True,

            "copper_cut_depth": 0.4,
            "hole_cut_depth": 1,
            "silkscreen_cut_depth": 0.1,
        }


    def __create_gcode_header(self, settings, xy_max, xy_min):
        return f"""
;Header Start
;header_type: cnc
;tool_head: {settings['tool_head']}
;machine: {settings['machine']}
;gcode_flavor: marlin
;renderMethod: line
;max_power: {settings['max_power']}
;file_total_lines: FILE_TOTAL_LINE_COUNT
;estimated_time(s): ESTIMATED_TIME
;is_rotate: false
;diameter: 0
;max_x(mm): {xy_max[0]}
;max_y(mm): {xy_max[1]}
;max_z(mm): 80
;max_b(mm): 0
;min_x(mm): {xy_min[0]}
;min_y(mm): {xy_min[1]}
;min_b(mm): 0
;min_z(mm): -3.5
;work_speed(mm/minute): {settings['work_speed(mm/min)']}
;jog_speed(mm/minute): {settings['jog_speed(mm/min)']}
;power(%): {settings['power (%)']}
;work_size_x: 400
;work_size_y: 400
;origin: bottom-left
;Header End
;PCB_To_CNC v{self.version}
; Made by Daniel Dobromylskyj (https://www.github.com/DanielDobromylskyj)
; G-code START <<<"""

    def create_silkscreen_unsafe(self, settings, xy_max, xy_min):
        gcode = self.__create_gcode_header(settings, xy_max, xy_min)
        gcode += f"\nG0 X0 Y0 Z5"

        CUT_HEIGHT = -settings["silkscreen_cut_depth"]

        x, y = 0, 0
        for command in self.topSilkscreen.commands:
            if command[0] == "draw":
                _, x1, y1, x2, y2, width = command

                if x != x1 or y != y1:
                    gcode += f"\nG0 Z5"
                    gcode += f"\nG0 X{x1} Y{-y1}"
                    gcode += f"\nG1 Z{CUT_HEIGHT} F120"

                gcode += f"\nG1 X{x2} Y{-y2} F120"
                
                x, y = x2, -y2

        gcode += "\nM30"

        with open("silkscreen.cnc", "w") as f:
            f.write(gcode)

    def convert(self, settings: dict, log=None):
        config = json.load(open("config.json"))
        loaded_settings = json.load(open("pcb_settings.json"))

        settings["max_tool_width_at_4mm"] = float(loaded_settings["Trace Tool Width"][0])
        settings["hole_tool_width"] = float(loaded_settings["Hole Tool Width"][0])
        settings["separate_drill_gcode"] = loaded_settings["Separate Gcode"][0]
        settings["work_speed(mm/min)"] = float(loaded_settings["Work Speed"][0])
        settings["jog_speed(mm/min)"] = float(loaded_settings["Travel Speed"][0])
        settings["pcb_hole_outline_width"] = float(loaded_settings["Hole Outline Width"][0])
        settings["copper_cut_depth"] = float(loaded_settings["Copper Cut Depth"][0])
        settings["hole_cut_depth"] = float(loaded_settings["Though hole Depth"][0])
        settings["silkscreen_cut_depth"] = float(loaded_settings["Silkscreen Cut Depth"][0])

        scale = int(config["Performance"]["Resolution"]["selected"])

        if not log:
            log = ProgressLogger(8, "Processing")

        outline_points: list[tuple[float, float]] = [(command[1], command[2]) for command in self.outline.commands if command[0] == "draw"]

        min_xy = min(outline_points, key=lambda p: p[0])[0] - 1, min(outline_points, key=lambda p: p[1])[1] - 1
        max_xy = max(outline_points, key=lambda p: p[0])[0] + 1, max(outline_points, key=lambda p: p[1])[1] + 1

        self.create_silkscreen_unsafe(settings, max_xy, min_xy)

        gcode = self.__create_gcode_header(settings, max_xy, min_xy)

        # higher == better res, also slower
        top_layer = Image.new("1", (round((max_xy[0] - min_xy[0]) * scale), round((max_xy[1] - min_xy[1]) * scale)), 1)
        draw = ImageDraw.Draw(top_layer)

        for command in self.topLayer.commands:
            if command[0] == 'draw':
                _, x1, y1, x2, y2, width = command

                draw.line([round((x1-min_xy[0])*scale), round((y1-min_xy[1])*scale), round((x2-min_xy[0])*scale), round((y2-min_xy[1])*scale)], 0, round(width*scale))

        r_extra = settings["pcb_hole_outline_width"]
        for hole in self.plated_though_holes.holes:
            x, y, r = hole
            draw.ellipse(
                [
                    (x - min_xy[0] - (r + r_extra)) * scale,  # Left
                    (y - min_xy[1] - (r + r_extra)) * scale,  # Top
                    (x - min_xy[0] + (r + r_extra)) * scale,  # Right
                    (y - min_xy[1] + (r + r_extra)) * scale  # Bottom
                ],
                outline=0,  # Use a color like "black" or (0, 0, 0)
                width=1,  # Set stroke width
                fill=0
            )


        for hole in self.no_plated_though_holes.holes:
            x, y, r = hole
            draw.ellipse(
                [
                    (x - min_xy[0] - (r + r_extra)) * scale,  # Left
                    (y - min_xy[1] - (r + r_extra)) * scale,  # Top
                    (x - min_xy[0] + (r + r_extra)) * scale,  # Right
                    (y - min_xy[1] + (r + r_extra)) * scale  # Bottom
                ],
                outline=0,  # Use a color like "black" or (0, 0, 0)
                width=1,  # Set stroke width
                fill=0
            )



        for hole in self.vias.holes:
            x, y, r = hole
            draw.ellipse(
                [
                    (x - min_xy[0] - (r + r_extra)) * scale,  # Left
                    (y - min_xy[1] - (r + r_extra)) * scale,  # Top
                    (x - min_xy[0] + (r + r_extra)) * scale,  # Right
                    (y - min_xy[1] + (r + r_extra)) * scale  # Bottom
                ],
                outline=0,  # Use a color like "black" or (0, 0, 0)
                width=1,  # Set stroke width
                fill=0
            )


        for pad in self.topPasteMask.pad_locations:
            x, y = pad["pos"]

            definition = self.topPasteMask.pad_definitions[pad["shape"]]

            if pad["shape"] in self.topPasteMask.pad_shapes:
                shape = self.topPasteMask.pad_shapes[pad["shape"]]
            else:
                shape = self.topPasteMask.pad_shapes[definition["shape"]]

            pad_points = self.convert_shape_to_lines(shape, definition["params"])

            if len(pad_points) < 2:
                log.log("[WARNING] Invalid pad shape, skipping")
            else:
                draw.polygon([(((x-min_xy[0]) + px)*scale, ((y-min_xy[1]) + py)*scale) for px, py in pad_points], fill=0)

        log.log("Load")
        log.complete_single()

        if config["Performance"]["Hardware"]["selected"] == "Use GPU":
            top_layer_outline = gpu_create_outline(log, top_layer, round((settings["max_tool_width_at_4mm"] * scale) / 2))
        else:
            top_layer_outline = self.__create_outline(log, top_layer, round((settings["max_tool_width_at_4mm"] * scale) / 2))

        log.log("Outlined")
        log.complete_single()

        holes = {
            "via": [(x-min_xy[0], y-min_xy[1], diameter) for x, y, diameter in self.vias.holes],
            "NP_Though": [(x-min_xy[0], y-min_xy[1], diameter) for x, y, diameter in self.no_plated_though_holes.holes],
            "P_Though": [(x-min_xy[0], y-min_xy[1], diameter) for x, y, diameter in self.plated_though_holes.holes],
        }

        empty_holes = {
            "via": [],
            "NP_Though": [],
            "P_Though": [],
        }

        holes_for_gcode = empty_holes if settings["separate_drill_gcode"] else holes

        gcode, eta = convert_image_to_gcode(log, gcode, holes_for_gcode, top_layer_outline, scale, settings, outline_points)

        gcode = gcode.replace("FILE_TOTAL_LINE_COUNT", str(len(gcode.split("\n"))))
        gcode = gcode.replace("ESTIMATED_TIME", str(round(eta)))

        print(f"\nLine Count: {len(gcode.split("\n"))}")
        print(f"Estimated time: {round(eta)}s ({int(eta // 3600)}h:{int((eta - ((eta // 3600) * 3600)) // 60)}m:{round(eta - ((eta - ((eta // 3600) * 3600)) // 60) * 60)}s)")

        with open("output.cnc", "w") as f:
            f.write(gcode)

        if settings["separate_drill_gcode"]:
            tmp = settings["max_tool_width_at_4mm"]
            settings["max_tool_width_at_4mm"] = settings["hole_tool_width"]
            empty_image = Image.new("1", (4, 4))

            gcode2 = self.__create_gcode_header(settings, max_xy, min_xy)
            gcode2, eta = convert_image_to_gcode(log, gcode2, holes, empty_image, scale, settings, outline_points)

            gcode2 = gcode2.replace("FILE_TOTAL_LINE_COUNT", str(len(gcode2.split("\n"))))
            gcode2 = gcode2.replace("ESTIMATED_TIME", str(round(eta)))

            print(f"\nLine Count: {len(gcode2.split("\n"))}")
            print(f"Estimated time: {round(eta)}s ({int(eta // 3600)}h:{int((eta - ((eta // 3600) * 3600)) // 60)}m:{round(eta - ((eta - ((eta // 3600) * 3600)) // 60) * 60)}s)")

            with open("drill_holes.cnc", "w") as f:
                f.write(gcode2)

            settings["max_tool_width_at_4mm"] = tmp

            print("Output sent to 'drill_holes.cnc'")

    @staticmethod
    def __create_outline(log, img, outline_width):  # GPU based option can be used now (gpu_path_generator.create_outline(log, img, width))
        outline = Image.new("1", img.size, 1)
        img_copy = img.convert("1")

        positions = [(-1, 0), (1, 0), (0, -1), (0, 1), (1, 1), (1, -1), (-1, -1), (-1, 1)]

        for i in range(outline_width):
            working_copy = img_copy.copy()
            pixels = img_copy.load()
            working_pixels = working_copy.load()
            outline_pixels = outline.load()

            width, height = img_copy.size
            for x in range(width):
                for y in range(height):
                    if pixels[x, y] == 1:  # Empty
                        if any(
                                0 <= x + dx < width and 0 <= y + dy < height and pixels[x + dx, y + dy] == 0
                                for dx, dy in positions
                        ):
                            working_pixels[x, y] = 0
                            if i == outline_width - 1:
                                outline_pixels[x, y] = 0

            img_copy = working_copy

        return outline

    def render(self, output=None):
        """Render parsed Gerber with matplotlib."""
        outline_points: list[tuple[float, float]] = [(command[1], command[2]) for command in self.outline.commands if command[0] == "draw"]

        min_xy = min(outline_points, key=lambda p: p[0])[0] - 1, min(outline_points, key=lambda p: p[1])[1] - 1
        max_xy = max(outline_points, key=lambda p: p[0])[0] + 1, max(outline_points, key=lambda p: p[1])[1] + 1

        width_pixels = (max_xy[0] - min_xy[0]) * 10
        height_pixels = (max_xy[1] - min_xy[1]) * 10
        dpi = 50

        fig_width = width_pixels / dpi
        fig_height = height_pixels / dpi

        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi, facecolor=(184/255, 115/255, 51/255))

        for command in self.topSilkscreen.commands:
            if command[0] == 'draw':
                _, x1, y1, x2, y2, width = command
                ax.plot([x1, x2], [y1, y2], 'y-', linewidth=1.5)

        for pad in self.topPasteMask.pad_locations:
            definition = self.topPasteMask.pad_definitions[pad["shape"]]

            if pad["shape"] in self.topPasteMask.pad_shapes:
                shape = self.topPasteMask.pad_shapes[pad["shape"]]
            else:
                shape = self.topPasteMask.pad_shapes[definition["shape"]]

            points = self.convert_shape_to_lines(shape, definition["params"])

            if points:
                x, y = pad["pos"]
                points = [(x + px, y + py) for px, py in points]

                polygon = Polygon(points, closed=True, color='red', alpha=1)
                ax.add_patch(polygon)


        for command in self.topLayer.commands:
            if command[0] == 'draw':
                _, x1, y1, x2, y2, width = command
                ax.plot([x1, x2], [y1, y2], 'k-', linewidth=width*2)

        for command in self.bottomLayer.commands:
            if command[0] == 'draw':
                _, x1, y1, x2, y2, width = command
                ax.plot([x1, x2], [y1, y2], 'b-', linewidth=width*2)


        ax.plot([], [], 'ro', label="Via (mostly under blue)")
        for x, y, size in self.vias.holes:
            circle = plt.Circle((x, y), size/2, color='red', fill=True, alpha=0.5)
            ax.add_patch(circle)

        ax.plot([], [], 'go', label="No Plate Drill Hole")
        for x, y, size in self.no_plated_though_holes.holes:
            circle = plt.Circle((x, y), size/2, color='green', fill=True, alpha=0.5)
            ax.add_patch(circle)

        ax.plot([], [], 'bo', label="Plated Drill Hole")
        for x, y, size in self.plated_though_holes.holes:
            circle = plt.Circle((x, y), size/2, color='blue', fill=True, alpha=0.5)
            ax.add_patch(circle)


        ax.set_aspect('equal')
        plt.grid(False)


        if output is None:
            plt.show()
        else:
            ax.set_axis_off()
            plt.savefig(output)

if __name__ == "__main__":
    path = input("Path (Do not include any quotation marks, Using '/' not '\\'): ").replace("\\", "/")

    if path == "":
        path = "battery_test_gerber/"

    print("[WARNING] You may need to close Gerber preview to continue")

    x = PCB(path)
    x.render()

    x.convert(PCB.default_settings())

    print("Output sent to 'output.cnc'")


