import pygame

import gui_render
import main as main_pcb


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

        self.pcb_image = None

        self.angles = [0, 0, 0]
        self.dx = 0
        self.dy = -100

    def load(self):
        self.surface.fill((100, 100, 100))

        if self.pcb:
            self.pcb.render("tmp/latest_board.png")
            self.pcb_image = gui_render.load_texture("tmp/latest_board.png")

        self.loaded = True

    def render(self):
        self.surface.fill((100, 100, 100))

        if self.pcb_image is not None:
            gui_render.draw_cuboid(self.surface, self.pcb_image, self.pcb_image.shape[1], self.pcb_image.shape[0], 5, self.angles[0], self.angles[1], self.angles[2], dx=self.dx, dy=self.dy)


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
            self.hidden_surface,
            (0, 0, 0, 255),
            (0, 0, round(self.width * (self.variable.get() / 100)), self.height),
            width=3,
            border_radius=3,
        )


def main(path=None):
    pygame.init()

    screen = pygame.display.set_mode((800, 600))
    clock = pygame.time.Clock()

    completion_progress_var = Variable(0)

    pcb = main_pcb.PCB(path) if path else None
    preview = RenderPreview(600, 780, pcb)

    sub_windows = [
        (TopSectorMenu(800, 20), (0, 0)),
        (preview, (200, 20)),
        (ProgressBar(500, 20, completion_progress_var), (250, 570)),
    ]

    rotating_pcb = False
    pcb_rotation_scale = 0.5

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

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
if __name__:
    main("battery_test_gerber")
