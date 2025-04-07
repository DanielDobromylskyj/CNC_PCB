from .reader import extract_line_data
from .value_parser import ValueParser


class TraceLayer:
    def __init__(self, fp):
        self.commands = []

        # Default values (assumed)
        self.x_value_parser = ValueParser(True, True, 4, 5)
        self.y_value_parser = ValueParser(True, True, 4, 5)

        self.__load(fp)

    def __load(self, fp) -> None:
        for line in fp.read().split("\n"):
            if line.startswith(";"):
                continue

            if line.startswith("%FS"):


            values = extract_line_data(line)

            if values:
                if "G" in values and values["G"] == "04":
                    continue  # Comment


