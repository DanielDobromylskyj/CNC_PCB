from .reader import extract_line_data
from .value_parser import ValueParser


class TraceLayer:
    def __init__(self, fp):
        self.commands = []

        # Default values (assumed)
        self.x_value_parser = ValueParser(True, True, 4, 5)
        self.y_value_parser = ValueParser(True, True, 4, 5)

        self.__load(fp)

    def __set_format_spec(self, line):
        leading_zeros = line[3] == "L"
        is_abs = line[4] == "A"

        x_pre, x_aft = int(line[6]), int(line[7])
        y_pre, y_aft = int(line[8]), int(line[9])

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
        for line in fp.read().split("\n"):
            if line.startswith(";"):
                continue

            if line.startswith("%FS"):
                self.__set_format_spec(line)

            if line.startswith("%MO"):
                self.__set_mode_units(line)


            values = extract_line_data(line)

            if values:
                if "G" in values and values["G"] == "04":
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



