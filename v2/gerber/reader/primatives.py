from copy import deepcopy
import math

def get_defaults():
    return deepcopy({
            "C": {
                "primitive": "circle",
                "params": ["1", "$1"]
            },

            "R": {
                "primitive": "rect",
                "params": ["1", "$1", "$2"]
            },

            "O": {
                "primitive": "oval_rect",
                "params": ["1", "$1", "$2"]
            }
        })


class ApertureMacroManager:
    def __init__(self):
        self.macro_shapes: dict = get_defaults()
        self.macro_definitions: dict = {}

        self.current_macro: None | str = None

    def define_aperture_macro(self, line: str) -> None:
        macro_shape = line.split("*")[0][3:]
        chunks = line.split("*")[1].split(",")

        self.macro_shapes[macro_shape] = {
            "primitive": chunks[0],
            "params": chunks[1:]
        }

    def define_aperture(self, line: str) -> None:
        macro_num = line[4:6]
        chunks = line.split("*")[0].split(",")

        # Store the pad definition with pad number as the key
        self.macro_definitions[macro_num] = {
            "shape": chunks[0][len("%ADDXY"):],
            "params": chunks[1].split("X") if len(chunks) > 1 else []
        }

    def set_aperture(self, name: str) -> None:
        if name not in self.macro_definitions:
            raise KeyError(f"{name} is not a defined macro / aperture")

        self.current_macro = name

    def get_aperture(self) -> dict:
        return self.macro_definitions[self.current_macro]


    def __getattr__(self, name: str) -> object:
        """ Retrieve loaded segment """
        if name not in self.macro_definitions:
            raise AttributeError(name)

        return self.macro_definitions[name]

    def __contains__(self, name: str) -> bool:
        """ Check to see if we have loaded a segment """
        return name in self.macro_definitions




def primitive_to_lines(shape, def_params):
    params = []
    for i, param in enumerate(shape["params"]):
        if param.startswith("$"):
            if int(param[1:]) > len(def_params):
                raise IndexError("Too little params when converting shape to lines")
            params.append(float(def_params[int(param[1:]) - 1]))
        else:
            params.append(float(param))

    if shape["primitive"] == '21':  # Rectangle with rounded corners
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
            return [(r * math.cos(a), r * math.sin(a)) for a in [i * (2 * math.pi / 50) for i in range(50)]]

    elif shape["primitive"] == "oval_rect":
        visible, width, height = params
        r = max(width/2, height/2)
        return primitive_to_lines({"primitive": "21", "params": ["1", "$1", "$2", "0", "0", "$3"]}, (width, height, r))

    elif shape["primitive"] == "rect":  # high jacking myself self
        return primitive_to_lines({"primitive": "21", "params": ["1", "$1", "$2", "0", "0", "0"]}, params)

    elif shape["primitive"] == "4":
        visible, vert_count = params[:2]

        if visible == 1:
            vertices = params[2:2 + ((int(vert_count) + 1) * 2)]
            rotation = params[-1]

            if rotation != 0:
                raise NotImplementedError("Rotation of a primitive (4) is not yet supported")

            return [(vertices[vertex_index * 2], vertices[(vertex_index * 2) + 1]) for vertex_index in
                    range(int(vert_count))]

    else:
        raise NotImplementedError(f"Unknown Primitive '{shape['primitive']}'")

    return []
