import pygame
from tkinter import Tk, filedialog

from gerber.pcb import PCB


root = Tk()
root.withdraw()  # Hide the root window


class App:
    def __init__(self, path=None):
        self.path = path
        self.pcb = self.load_pcb(path) if path else None

        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption('PCB CNC')


    def load_file(self):
        file_path = filedialog.askopenfilename()
        self.pcb = self.load_pcb(file_path) if file_path else None


    def load_pcb(self, path):
        return PCB(path)


    def run(self):
        self.running = True

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

        pygame.quit()


if __name__ == '__main__':
    App().run()