import os

from . import zip_manager
from .reader import trace_layer
import math

class PCB:
    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        self.path = path
        self.min_xy = [math.inf, math.inf]
        self.max_xy = [-math.inf, -math.inf]

        self.__components = {}
        self.__component_colours = {}

        self.__load()

    def __load(self) -> None:
        possible_files = [
            # Gerber Filename            Parser            Internal name   Colour
            ("Gerber_TopLayer.GTL", trace_layer.TraceLayer, "TopLayer", (255, 0, 0)),
            ("Gerber_TopSilkscreenLayer.GTO", trace_layer.TraceLayer, "TopSilk", (255, 255, 0)),
        ]

        with zip_manager.GerberFile(self.path) as gerber_file:
            for file, loader, key, colour in possible_files:
                file_obj = gerber_file.open(file, "r")

                if file_obj:
                    loaded_obj = loader(file_obj)
                    self.__components[key] = loaded_obj
                    self.__component_colours[key] = colour

                    if loaded_obj.min_xy[0] < self.min_xy[0]: self.min_xy[0] = loaded_obj.min_xy[0]
                    if loaded_obj.max_xy[0] > self.max_xy[0]: self.max_xy[0] = loaded_obj.max_xy[0]
                    if loaded_obj.min_xy[1] < self.min_xy[1]: self.min_xy[1] = loaded_obj.min_xy[1]
                    if loaded_obj.max_xy[1] > self.max_xy[1]: self.max_xy[1] = loaded_obj.max_xy[1]

    def get_component_colour(self, name):
        return self.__component_colours[name]

    def get_component(self, name):
        return self.__components[name]

    def __getattr__(self, name: str) -> object:
        """ Retrieve loaded segment """
        if name not in self.__components:
            raise AttributeError(name)

        return self.__components[name]

    def __contains__(self, name: str) -> bool:
        """ Check to see if we have loaded a segment """
        return name in self.__components

    def __iter__(self):
        """ Iterate over loaded segments """
        return iter(self.__components.keys())