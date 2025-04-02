# CNC_PCB

## Overview

This is a program to convert a extracted gerber file into a .cnc file containing gcode (All tests run on CAMotics and Snapmaker 3 in 1 CNC - Artisan?)

## Features

- **Flexible Configuration**: Supports custom sized CNC tools, and will attempt to create the best gcode for the given tool
- **Python 3.12 Compatibility**: Built and tested in Python 3.12.
- **Not Very Powerfull Viewer**: Builtin PCB viewer (and Gcode previewer - One day)

## Requirements

- **Python 3.12**
- **Dependencies (As of v0.3)**:
  - `pillow`
  - `matplotlib` (for visualizations, optional)
  - `pygame` (For App)
  - `cv2` (For App)
  - `numpy` (For App)

Install dependencies with:
```bash
py -m pip install pillow matplotlib opencv-python pygame numpy
```

## Usage
This is for the module, not GUI
   ```python
    # Import from whatever it is called if I turn this to a module
    from main import PCB

    path = r"path/to/extracted/gerber/"
    pcb = PCB(path)

    # Render with matplotlib
    pcb.render()  # parse a path as a string to save as an image

    # Converting to Gcode
    config = PCB.default_settings()  # Feel free to edit this dict
    pcb.convert(config)  # Outputs as 'output.cnc'    
   ```
