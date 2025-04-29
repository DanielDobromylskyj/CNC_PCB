from gerber.pcb import PCB
from gerber.render import renderer
from gerber.cnc import convertor, settings

pcb = PCB(r"mouse.zip")

"""preview = renderer.render_pcb(pcb, is_in_colour=True)
preview.show()"""

convertor.convert(pcb, settings.DefaultSettings, output_path="output")
