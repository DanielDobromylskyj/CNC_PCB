import os

from . import zip_manager
from .reader import trace_layer


class PCB:
    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        self.path = path
        self.__components = {}

        self.__load()

    def __load(self) -> None:
        possible_files = [
            # Gerber Filename            Parser            Internal name
            ("Gerber_TopLayer.GTL", trace_layer.TraceLayer, "TopLayer")
        ]

        with zip_manager.GerberFile(self.path) as gerber_file:
            for file, loader, key in possible_files:
                file_obj = gerber_file.open(file, "r")

                if file_obj:
                    loaded_obj = loader(file_obj)
                    self.__components[key] = loaded_obj

    def __getattr__(self, name: str) -> object:
        """ Retrieve loaded segment """
        if name not in self.__components:
            raise AttributeError(name)

        return self.__components[name]

    def __contains__(self, name: str) -> bool:
        """ Check to see if we have loaded a segment """
        return name in self.__components