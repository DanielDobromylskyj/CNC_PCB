if line.startswith("G"):
    draw_mode = int(line[1:3])

# Match coordinates (e.g., X12345Y67890D01)
match = re.search(r'X([-]?\d+)Y([-]?\d+)(?:D0([123]))?', line)
if match:
    new_x, new_y = int(match.group(1)) / 100000, int(match.group(2)) / 100000
    d_code = match.group(3)

    # Use the active aperture width, default to 0.2mm if unknown
    width = self.apertures.get(active_aperture, 0.2)

    if d_code == "1" and x is not None and y is not None:  # Draw line (D01)
        if draw_mode == 1:
            self.commands.append(('draw', x, y, new_x, new_y, width))
        else:
            raise Exception("Draw mode not defined")

    elif d_code == "2" or x is None or y is None:  # Move (D02)
        self.commands.append(('move', new_x, new_y))

    elif d_code is None:
        if draw_mode == 2:
            x_end, y_end, i, j, d = read_arc(line, 4, 5)

            start_x = x
            start_y = y

            center_x = start_x + i
            center_y = start_y + j

            radius = math.sqrt(i ** 2 + j ** 2)

            start_angle = math.atan2(start_y - center_y, start_x - center_x)
            end_angle = math.atan2(y_end - center_y, x_end - center_x)

            if end_angle < start_angle:
                end_angle += 2 * math.pi

            angle_step = (end_angle - start_angle) / 20

            # Generate the points along the arc using list comprehension
            arc_points = [(center_x + radius * math.cos(start_angle + i * angle_step),
                           center_y + radius * math.sin(start_angle + i * angle_step))
                          for i in range(20 + 1)]

            new_x, new_y = arc_points[-1]
            for i, point in enumerate(arc_points[1:]):
                self.commands.append(
                    ('draw', point[0], point[1], arc_points[i][0], arc_points[i][1], width))

    x, y = new_x, new_y  # Update position