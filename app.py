import threading
import time

import pygame
from tkinter.filedialog import askdirectory

import gui_render
import main as main_pcb
from logger import ProgressLogger


class LoggerCapture(ProgressLogger):
    def __init__(self, size, blocks=40):
        super().__init__(size, blocks=blocks)
        print("\r", end="")

        self.status = 0
        self.nudge_value = 1 / size
        self.count = 0


    def __display_progress(self, force=False):
        pass

    def complete_single(self):
        self.status += self.nudge_value
        self.status = min(self.status, 1)

        self.count += 1

    def log(self, text):
        pass


class Processor:
    def __init__(self):
        self.pcb = None
        self.logger = None

    def get_value(self):
        if self.logger is None:
            return 0

        return self.logger.status

    def reset(self):
        self.logger = None

    def start(self, pcb, settings):
        steps = 9

        self.logger = LoggerCapture(steps)
        pcb.convert(settings, self.logger)


class TopSectorMenu:
    def __init__(self, width, height):
        self.surface = pygame.Surface((width, height))
        self.width = width
        self.height = height
        self.loaded = False

        self.font = pygame.sysfont.SysFont("monospace", 20)

    def load(self):
        self.surface.fill((250, 250, 250))

        x = 0
        text = self.font.render("File", True, (0, 0, 0))
        self.surface.blit(text, (x+5, (self.height / 2) - (text.get_height() / 2)))
        x += text.get_width() + 10

        pygame.draw.line(
            self.surface,
            (0, 0, 0),
            (x, 0), (x, self.height),
        )

        text = self.font.render("Config", True, (0, 0, 0))
        self.surface.blit(text, (x+5, (self.height / 2) - (text.get_height() / 2)))
        x += text.get_width() + 10

        pygame.draw.line(
            self.surface,
            (0, 0, 0),
            (x, 0), (x, self.height),
        )

        text = self.font.render("Help", True, (0, 0, 0))
        self.surface.blit(text, (x + 5, (self.height / 2) - (text.get_height() / 2)))
        x += text.get_width() + 10

        pygame.draw.line(
            self.surface,
            (0, 0, 0),
            (x, 0), (x, self.height),
        )



        self.loaded = True

    def render(self):
        pass

class RenderPreview:
    def __init__(self, width, height, pcb):
        self.surface = pygame.Surface((width, height))
        self.width = width
        self.height = height
        self.pcb = pcb
        self.loaded = False

        self.font = pygame.sysfont.SysFont("monospace", 38)

        self.prev_pcb = Variable(None)

        self.pcb_image = None

        self.angles = [0, 0, 0]
        self.dx = 0
        self.dy = -100

    def load(self):
        self.surface.fill((100, 100, 100))
        pcb = self.pcb.get()

        if pcb:
            if pcb.size[0] > 200 or pcb.size[1] > 200:
                return

            pcb.render("tmp/latest_board.png")
            self.pcb_image = gui_render.load_texture("tmp/latest_board.png")

        self.loaded = True

    def render(self):
        self.surface.fill((100, 100, 100))

        if self.prev_pcb.get() != self.pcb.get():
            self.load()
            self.prev_pcb.set(self.pcb.get())


        if self.pcb_image is not None:
            gui_render.draw_cuboid(self.surface, self.pcb_image, self.pcb_image.shape[1], self.pcb_image.shape[0], 5, self.angles[0], self.angles[1], self.angles[2], dx=self.dx, dy=self.dy)

        else:
            if self.pcb.get() is not None:
                text = self.font.render("Size To Large To Render", True, (0, 0, 0))
                self.surface.blit(text, (0, 0))

class Variable:
    def __init__(self, value):
        self.__value = value

    def set(self, value):
        self.__value = value

    def get(self):
        return self.__value

class ProgressBar:
    def __init__(self, width, height, var):
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.hidden_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width
        self.height = height
        self.variable = var
        self.loaded = False

    def load(self):
        pygame.draw.rect(
            self.hidden_surface,
            (200, 200, 200, 255),
            (0, 0, self.width, self.height),
            border_radius=3,
        )

        pygame.draw.rect(
            self.hidden_surface,
            (0, 0, 0, 255),
            (0, 0, self.width, self.height),
            width=3,
            border_radius=3,
        )

        self.surface.blit(self.hidden_surface, (0, 0))
        self.loaded = True

    def render(self):
        self.surface.blit(self.hidden_surface, (0, 0))

        pygame.draw.rect(
            self.surface,
            (10, 255, 10, 255),
            (0, 0, round(self.width * self.variable.get()), self.height),
            border_radius=3,
        )

        pygame.draw.rect(
            self.surface,
            (0, 0, 0, 255),
            (0, 0, self.width, self.height),
            width=3,
            border_radius=3,
        )


class pcb_processor:
    def __init__(self, width, height, pcb_var):
        self.surface = pygame.Surface((width, height))
        self.width = width
        self.height = height
        self.pcb_var = pcb_var
        self.loaded = False
        self.prev_pcb = Variable(None)

        self.font = pygame.sysfont.SysFont("monospace", 20)
        self.generation_data = {}
        self.gen_button_rect = None

    def load(self):
        self.surface.fill((200,200,200))

        pcb = self.pcb_var.get()
        if pcb is not None:
            if not self.generation_data:
                text = self.font.render("Generate Gcode", True, (0, 0, 0))
                self.gen_button_rect = text.get_rect()
                self.gen_button_rect.topleft = (10, 10)

                pygame.draw.rect(
                    self.surface,
                    (0, 0, 0),
                    self.gen_button_rect,
                    width=2
                )
                self.surface.blit(text, (10, 10))




        self.loaded = True

    def render(self):
        if self.prev_pcb.get() != self.pcb_var.get():
            self.load()
            self.prev_pcb.set(self.pcb_var.get())

def open_file(pcb_var):
    path = askdirectory(title="PCB Gerber Selector")

    if path:
        pcb_var.set(main_pcb.PCB(path))


def process_pcb(pcb_var, pcb_prc, completion_progress_var, settings):
    pcb_prc.reset()

    threading.Thread(target=pcb_prc.start, args=(pcb_var.get(), settings)).start()

    while True:
        completion_progress_var.set(pcb_prc.get_value())
        time.sleep(0.01)

        if pcb_prc.get_value() >= 1:
            completion_progress_var.set(pcb_prc.get_value())
            return


SELECT_TYPE_MAX_ONE = 0

def main(path=None):
    pygame.init()

    screen = pygame.display.set_mode((800, 600))
    clock = pygame.time.Clock()

    completion_progress_var = Variable(0)

    pcb = main_pcb.PCB(path) if path else None
    pcb_var = Variable(pcb)


    preview = RenderPreview(600, 780, pcb_var)
    pcb_prc = Processor()
    pcb_prc_display = pcb_processor(200, 580, pcb_var)

    sub_windows = [
        (TopSectorMenu(800, 20), (0, 0)),
        (preview, (200, 20)),
        (ProgressBar(500, 20, completion_progress_var), (250, 570)),
        (pcb_prc_display, (0, 20))
    ]

    rotating_pcb = False
    pcb_rotation_scale = 0.5

    config_menu_open = False

    config_path = "@@"
    config_menu = {
        "machine": {
            "type": SELECT_TYPE_MAX_ONE,
            "selected": 0,
            "options": [
                "Snapmaker 3in1",
                "Test option",
                "Test option2"
            ]
        }
    }

    settings = main_pcb.PCB.default_settings()
    settings["max_tool_width_at_4mm"] = 0.2

    running = True
    loading = [True, 0]
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # left click
                    x, y = event.pos

                    if (x > 200) and (y > 20):
                        rotating_pcb = True

                    if (0 <= x <= 60) and (y < 20):
                        threading.Thread(target=open_file, args=(pcb_var,)).start()

                    if (60 <= x <= 140) and (y < 20):
                        print("Config")

                    if (140 <= x <= 200) and (y < 20):
                        print("HELP")

                    if pcb_prc_display.gen_button_rect is not None and pcb_prc_display.gen_button_rect.collidepoint(x, y - 20):
                        threading.Thread(target=process_pcb, args=(pcb_var, pcb_prc, completion_progress_var, settings)).start()

            if event.type == pygame.MOUSEMOTION:
                dx, dy = event.rel

                if rotating_pcb:
                    preview.angles[1] -= dx * pcb_rotation_scale
                    preview.angles[0] -= dy * pcb_rotation_scale


            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if rotating_pcb:
                        rotating_pcb = False



        screen.fill((200,200,200))


        if loading[0]:
            if loading[1] < len(sub_windows):
                sub_window, xy = sub_windows[loading[1]]
                sub_window.load()
                loading[1] += 1

            else:
                loading[0] = False
        for sub_window, xy in sub_windows:
            if sub_window.loaded:
                sub_window.render()

            screen.blit(sub_window.surface, xy)


        if config_menu_open:
            pass


        pygame.display.flip()

        clock.tick(60)

    pygame.quit()
if __name__:
    main()
