import time


class bcolors:
    HEADER = '\033[95m'
    ENDC = '\033[0m'

    GREEN = '\033[92m'
    ORANGE = '\033[93m'
    RED = '\033[91m'

class ProgressLogger:
    def __init__(self, size=None, display_text="Working", blocks=40):
        self.size = size

        self.blocks = blocks
        self.display_text = display_text

        self.current = 0
        self.start = 0
        self.last_display = 0

        self.__display_progress()


    def complete_single(self):
        if self.current == self.size - 1:
            self.__display_progress(force=True)
            print()  # reset lines

        self.__display_progress()
        self.current += 1

    def log(self, text):
        print(f"\r{self.display_text} {text}{' ' * (len(self.display_text) + 20 + self.blocks - len(text))}")
        self.__display_progress(force=True)

    def __display_progress(self, force=False):
        if (self.last_display + 0.1 > time.time()) and not force:
            return


        percent_complete = self.current / self.size
        block_percent = round(percent_complete * self.blocks)

        step_size = 255 / self.blocks

        red = 255 - round(block_percent * step_size)  # Decreasing red
        green = round(block_percent * step_size)  # Increasing green
        color_code = f"\033[38;2;{red};{green};0m"

        print(f"\r{bcolors.GREEN}{self.display_text}{bcolors.ENDC} {color_code}{round(percent_complete * 100, 1)}%{bcolors.ENDC} |", end="", flush=True)

        for i in range(block_percent):
            red = 255 - round(i * step_size)  # Decreasing red
            green = round(i * step_size) # Increasing green
            color_code = f"\033[38;2;{red};{green};0m"
            print(f"{color_code}█", end="", flush=True)

        print(f"{bcolors.ENDC}{' ' * (self.blocks - block_percent)}|", end="", flush=True)

        self.last_display = time.time()
