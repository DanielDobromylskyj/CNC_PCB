from .reader import extract_line_data
from .value_parser import ValueParser
from .primatives import ApertureMacroManager, primitive_to_lines



class TraceLayer:
    def __init__(self, fp):
        self.commands = []

        self.aperture_macros = ApertureMacroManager()

        # Default values (assumed)
        self.x_value_parser = ValueParser(True, True, 4, 5)
        self.y_value_parser = ValueParser(True, True, 4, 5)

        self.__load(fp)

    def __set_format_spec(self, line):
        leading_zeros = line[3] == "L"
        is_abs = line[4] == "A"

        x_pre, x_aft = int(line[6]), int(line[7])
        y_pre, y_aft = int(line[9]), int(line[10])

        self.x_value_parser.leading_zeros = leading_zeros
        self.y_value_parser.leading_zeros = leading_zeros

        self.x_value_parser.absolute = is_abs
        self.y_value_parser.absolute = is_abs

        self.x_value_parser.before_decimal = x_pre
        self.y_value_parser.before_decimal = y_pre

        self.x_value_parser.after_decimal = x_aft
        self.y_value_parser.after_decimal = y_aft

    def __set_mode_units(self, line):
        units = line[3:4]

        self.x_value_parser.units = units
        self.y_value_parser.units = units

    def __load(self, fp) -> None:
        g_mode = None
        last_x, last_y = 0, 0

        for line in fp.read().split("\n"):
            if line.startswith(";"):
                continue

            if line.startswith("%FS"):
                self.__set_format_spec(line)

            if line.startswith("%MO"):
                self.__set_mode_units(line)

            if line.startswith("%AM"):
                self.aperture_macros.define_aperture_macro(line)

            if line.startswith('%ADD'):
                self.aperture_macros.define_aperture(line)


            values = extract_line_data(line)

            if values:
                if "G" in values:
                    if values["G"] == "04":
                        continue  # Comment

                    g_mode = values["G"]



                if "D" in values and values["D"] in self.aperture_macros:
                    self.aperture_macros.set_aperture(values["D"])


                if "X" in values and "Y" in values:
                    x_pos, y_pos = values["X"], values["Y"]
                    active_aperture = self.aperture_macros.get_aperture()

                    width = 0.2  # default trace width
                    if active_aperture["shape"] == "C":
                        width = active_aperture["params"][0]

                    if g_mode == "01":  # straight lines
                        if values["D"] == "01":
                            self.commands.append(
                                ("line", last_x, last_y, x_pos, y_pos, width)
                            )

                        elif values["D"] == "02":  # move, dont draw
                            last_x, last_y = x_pos, y_pos


                        elif values["D"] == "03":  # blit aperture
                            definition = self.aperture_macros.macro_definitions[active_aperture["shape"]]

                            if active_aperture["shape"] in self.aperture_macros.macro_shapes:
                                shape = self.aperture_macros.macro_shapes[active_aperture["shape"]]
                            else:
                                shape = self.aperture_macros.macro_shapes[definition["shape"]]

                            aperture_points = primitive_to_lines(shape, definition["params"])
                            aperture_points = [(x_pos + px, y_pos + py) for px, py in aperture_points]

                            self.commands.append(
                                ("blit", aperture_points)
                            )

                        else:
                            raise Exception(f"Unknown value for D when parsing a line.'{values["D"]}'")

                    elif g_mode == "02":  # arc
                        i, j, d = values["I"], values["J"], values["D"]

                        start_x = last_x
                        start_y = last_y

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

                        last_x, last_y = arc_points[-1]
                        for i, point in enumerate(arc_points[1:]):
                            self.commands.append(
                                ('draw', point[0], point[1], arc_points[i][0], arc_points[i][1], width))

                    elif g_mode == "03":  # arc (opposite rotation)
                        i, j, d = values["I"], values["J"], values["D"]

                        start_x = last_x
                        start_y = last_y

                        center_x = start_x + i
                        center_y = start_y + j

                        radius = math.sqrt(i ** 2 + j ** 2)

                        start_angle = math.atan2(start_y - center_y, start_x - center_x)
                        end_angle = math.atan2(values["Y"] - center_y, values["X"] - center_x)

                        if end_angle <= start_angle:
                            end_angle += 2 * math.pi

                        angle_step = (end_angle - start_angle) / 20


