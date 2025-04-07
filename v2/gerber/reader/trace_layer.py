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


            values = extract_line_data(line)

            if values:
                if "G" in values and values["G"] == "04":
                    continue  # Comment


