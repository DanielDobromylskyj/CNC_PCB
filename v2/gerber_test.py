from gerber.pcb import PCB
from gerber.render import renderer

pcb = PCB(r"bat_tester.zip")

#preview = renderer.render_pcb(pcb, is_in_colour=True)
#preview.show()

mask = renderer.render_pcb(pcb, is_in_colour=True)
mask.show()