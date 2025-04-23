from .reader import extract_line_data
from .value_parser import ValueParser
from .primatives import ApertureMacroManager, primitive_to_lines

import math

class ThoughHole:
    def __init__(self, fp):
        self.drill_sizes = {}
        self.current_drill = None

        self.min_xy = [math.inf, math.inf]
        self.max_xy = [-math.inf, -math.inf]

        # Default values (assumed)
        self.value_parser = ValueParser(True, True, 3, 3)

        self.commands = []
        self.__load(fp)

    def __set_format_spec(self, line):
        unit_type, zero_type, number_format = line.split(",")

        unit_lookup = {
            "METRIC": "MM"
        }

        if unit_type in unit_lookup:
            units = unit_lookup[unit_type]
        else:
            units = "IN"

        leading_zeros = zero_type == "LZ"
        pre = len(number_format.split(".")[0])
        aft = len(number_format.split(".")[1])

        self.value_parser.leading_zeros = leading_zeros

        self.value_parser.before_decimal = pre
        self.value_parser.after_decimal = aft
        self.value_parser.units = units

    def __set_abs(self, is_abs):
        self.value_parser.absolute = is_abs

    def __load(self, fp):
        for i, line in enumerate(fp.read().split("\n")):
            if line.startswith("\n"):
                continue

            if line.startswith(";"):
                continue

            if i == 1:
                self.__set_format_spec(line)

            values = extract_line_data(line)
            if "T" in values:
                if len(line) > 3:
                    if line[3] == "C":
                        self.drill_sizes[values["T"]] = float(values["C"])
                    else:
                        raise Exception(f"Unknown drill definition in though hole layer: {line}")

                else:
                    self.current_drill = values["T"]

            if "G" in values:
                if values["G"] == "90":
                    self.__set_abs(True)

                elif values["G"] == "91":
                    self.__set_abs(False)

            if "X" in values and "Y" in values:
                x_pos, y_pos = self.value_parser.parse_value(values["X"]), self.value_parser.parse_value(values["Y"])
                drill_size = self.drill_sizes[self.current_drill]

                if x_pos - (drill_size / 2) < self.min_xy[0]: self.min_xy[0] = x_pos - (drill_size / 2)
                if x_pos + (drill_size / 2) > self.max_xy[0]: self.max_xy[0] = x_pos + (drill_size / 2)
                if y_pos - (drill_size / 2) < self.min_xy[1]: self.min_xy[1] = y_pos - (drill_size / 2)
                if y_pos + (drill_size / 2) > self.max_xy[1]: self.max_xy[1] = y_pos + (drill_size / 2)

                self.commands.append(("hole", x_pos, y_pos, drill_size))


