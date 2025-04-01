import time


def to_g_coords(mode, x, y, z):
    return f"\nG{mode} X{x} Y{y} Z{z}"


def travel_time(xyz1, xyz2, speed):
    return (sum([(xyz2[i] - xyz1[i]) ** 2 for i in range(3)]) ** 0.5) * speed

def convert_image_to_gcode(log, header, holes, image, scale, settings, outline_points):
    gcode = header

    # I'm unsure why I use 600 to convert from min to sec, but it gives a better output.
    jog_speed = settings["jog_speed(mm/min)"] / 600  # per sec
    work_speed = settings["work_speed(mm/min)"] / 600  # per sec
    estimated_time = 0

    gcode += "\nG90"
    gcode += "\nG21"
    gcode += "\nG0 X0 Y0 Z8"
    gcode += f"\nG1 F{settings['work_speed(mm/min)']}"

    log.log("Trace Groups")

    sections = []
    for x in range(image.size[0]):
        for y in range(image.size[1]):
            pixel = image.getpixel((x, y))

            if pixel == 0:
                section = []
                px, py = x, y

                while True:
                    moves = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
                    found_move = False

                    for dx, dy in moves:
                        cx, cy = px + dx, py + dy

                        pixel = image.getpixel((cx, cy))

                        if pixel == 0:
                            image.putpixel((cx, cy), 1)
                            found_move = True
                            px, py = cx, cy
                            section.append((cx / scale, cy / scale))
                            break

                    if not found_move:
                        break

                sections.append(section)

    log.complete_single()

    log.log("Trace Gcode")

    TRAVEL_HEIGHT = 5
    CUT_HEIGHT =  -.4
    HOLE_HEIGHT = -1
    PRE_HOLE_HEIGHT = 1

    prev_xyz = [0, 0, 8]

    for section in sections:
        if len(section) == 0:
            continue

        x, y = section[0]
        gcode += to_g_coords(0, x, y, TRAVEL_HEIGHT)
        estimated_time += travel_time([x, y, TRAVEL_HEIGHT], prev_xyz, jog_speed)
        prev_xyz = [x, y, TRAVEL_HEIGHT]

        gcode += "\nM3 P100"  # start spinning
        gcode += to_g_coords(1, x, y, CUT_HEIGHT)
        estimated_time += travel_time([x, y, CUT_HEIGHT], prev_xyz, work_speed)
        prev_xyz = [x, y, CUT_HEIGHT]

        for point in section[1:]:
            x, y = point

            gcode += to_g_coords(1, x, y, CUT_HEIGHT)
            estimated_time += travel_time([x, y, CUT_HEIGHT], prev_xyz, work_speed)
            prev_xyz = [x, y, CUT_HEIGHT]

        x, y = section[-1]
        gcode += to_g_coords(1, x, y, TRAVEL_HEIGHT)
        estimated_time += travel_time([x, y, TRAVEL_HEIGHT], prev_xyz, work_speed)
        prev_xyz = [x, y, TRAVEL_HEIGHT]

        gcode += "\nM5"  # stop spinning

    log.complete_single()

    log.log("Hole Gcode")

    for hole in holes["P_Though"]:  # plated
        x, y, d = hole
        code, eta = hole_to_gcode(log, x, y, d, settings["max_tool_width_at_4mm"], PRE_HOLE_HEIGHT, HOLE_HEIGHT)
        gcode += code
        estimated_time += eta

    for hole in holes["NP_Though"]:  # plated
        x, y, d = hole
        code, eta = hole_to_gcode(log, x, y, d, settings["max_tool_width_at_4mm"], PRE_HOLE_HEIGHT, HOLE_HEIGHT)
        gcode += code
        estimated_time += eta

    for hole in holes["via"]:  # plated
        x, y, d = hole
        code, eta = hole_to_gcode(log, x, y, d, settings["max_tool_width_at_4mm"], PRE_HOLE_HEIGHT, HOLE_HEIGHT)
        gcode += code
        estimated_time += eta

    x, y = outline_points[0]
    gcode += to_g_coords(0, x, y, TRAVEL_HEIGHT)
    estimated_time += travel_time([x, y, TRAVEL_HEIGHT], prev_xyz, jog_speed)
    prev_xyz = [x, y, TRAVEL_HEIGHT]

    gcode += "\nM3 P100"
    for point in outline_points:
        x, y = point

        gcode += to_g_coords(1, x, y, HOLE_HEIGHT)
        estimated_time += travel_time([x, y, HOLE_HEIGHT], prev_xyz, work_speed)
        prev_xyz = [x, y, HOLE_HEIGHT]

    x, y = outline_points[0]
    gcode += to_g_coords(1, x, y, HOLE_HEIGHT)
    estimated_time += travel_time([x, y, HOLE_HEIGHT], prev_xyz, work_speed)
    prev_xyz = [x, y, HOLE_HEIGHT]

    gcode += "\nM5"

    x, y = outline_points[-1]
    gcode += to_g_coords(1, x, y, TRAVEL_HEIGHT)
    estimated_time += travel_time([x, y, TRAVEL_HEIGHT], prev_xyz, jog_speed)
    prev_xyz = [x, y, TRAVEL_HEIGHT]



    log.log("Complete")
    log.complete_single()
    return gcode + "\nM30", estimated_time


def hole_to_gcode(log, x, y, width, tool_width, SAFE_HEIGHT, HOLE_HEIGHT):
    gcode = ""

    estimated_time = 10  # Just a hardcoded guess, sucks to suck

    if width <= tool_width:
        gcode += to_g_coords(0, x, y, SAFE_HEIGHT)
        gcode += "\nM3 P100"  # start spinning

        for cut_height in range(round(SAFE_HEIGHT * 10), round(HOLE_HEIGHT * 10), -1 * 10):  # 1mm "pecks"
            gcode += to_g_coords(1, x, y, cut_height / 10)
            gcode += to_g_coords(0, x, y, SAFE_HEIGHT)

        gcode += to_g_coords(1, x, y, HOLE_HEIGHT)
        gcode += to_g_coords(0, x, y, SAFE_HEIGHT)

    else:
        log.log("[WARNING] Using Untested hole cutting")
        # Untested  - FIX ME / Better options are possible
        estimated_time = 40

        y -= ((width / 2) - (tool_width / 2))
        gcode += to_g_coords(0, x, y, SAFE_HEIGHT)
        gcode += "\nM3 P100"

        radius = width / 2
        tool_radius = tool_width / 2
        stepdown = 1

        for cut_height in range(round(SAFE_HEIGHT * 10), round(HOLE_HEIGHT * 10), -1 * stepdown * 10):
            depth = cut_height / 10

            gcode += to_g_coords(1, x, y, depth)
            gcode += f"\nG2 X{x} Y{y} I0 J{radius - tool_radius} Z{depth} F300"  # Circular cut

        gcode += f"\nG2 X{x} Y{y} I0 J{radius - tool_radius} Z{HOLE_HEIGHT} F300"
        gcode += to_g_coords(0, x, y, SAFE_HEIGHT)

    gcode += "\nM5"  # stop spinning
    return gcode, estimated_time

