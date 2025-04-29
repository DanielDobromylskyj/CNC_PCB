from .settings import Settings


def create_header(pcb, settings: Settings):
    return f"""
    ;Header Start
    ;header_type: cnc
    ;tool_head: {settings.tool_head}
    ;machine: {settings.machine}
    ;gcode_flavor: marlin
    ;renderMethod: line
    ;max_power: {settings.max_power}
    ;file_total_lines: FILE_TOTAL_LINE_COUNT
    ;estimated_time(s): ESTIMATED_TIME
    ;is_rotate: false
    ;diameter: 0
    ;max_x(mm): {pcb.max_xy[0]}
    ;max_y(mm): {pcb.max_xy[1]}
    ;max_z(mm): 80
    ;max_b(mm): 0
    ;min_x(mm): {pcb.min_xy[0]}
    ;min_y(mm): {pcb.min_xy[1]}
    ;min_b(mm): 0
    ;min_z(mm): -3.5
    ;work_speed(mm/minute): {settings.cut_speed}
    ;jog_speed(mm/minute): {settings.travel_speed}
    ;power(%): {settings.power}
    ;work_size_x: 400
    ;work_size_y: 400
    ;origin: bottom-left
    ;Header End
    ;PCB_To_CNC v2
    ; Made by Daniel Dobromylskyj (https://www.github.com/DanielDobromylskyj)
    ; G-code START <<<"""


class CNC_Gcode:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.gcode = ""


    def go_to(self, x, y, z):
        self.gcode += f"\nG00 X{x/self.settings.scale} Y{y/self.settings.scale} Z{z} F{self.settings.travel_speed}"

    def cut_to(self, x, y, z):
        self.gcode += f"\nG01 X{x/self.settings.scale} Y{y/self.settings.scale} Z{z} F{self.settings.cut_speed}"

    def spin(self, clockwise=True):
        if clockwise:
            self.gcode += f"\nM03 S{self.settings.spinal_rpm}"
        else:
            self.gcode += f"\nM04 S{self.settings.spinal_rpm}"

    def stop(self):
        self.gcode += "\nM05"