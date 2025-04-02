import pygame
import numpy as np
import cv2
import math

# Colors
COPPER = (184, 115, 51)  # Copper color
FR4 = (50, 120, 50)  # Green PCB color
WHITE = (255, 255, 255)



def get_warped_image_size(M, width, height):
    # Original image corners (x, y)
    corners = np.array([[0, 0],
                        [width - 1, 0],
                        [0, height - 1],
                        [width - 1, height - 1]], dtype="float32")

    # Add a column of ones for homogeneous coordinates
    ones = np.ones((corners.shape[0], 1))
    corners_homogeneous = np.hstack([corners, ones])

    # Apply the perspective transformation
    transformed_corners = M.dot(corners_homogeneous.T).T

    # Normalize the coordinates by dividing by the homogeneous coordinate
    transformed_corners /= transformed_corners[:, 2][:, np.newaxis]

    # Get the min/max x and y values of the transformed corners to find the new bounding box
    min_x = np.min(transformed_corners[:, 0])
    max_x = np.max(transformed_corners[:, 0])
    min_y = np.min(transformed_corners[:, 1])
    max_y = np.max(transformed_corners[:, 1])

    # The new image size is the width and height of the bounding box
    new_width = int(max_x - min_x)
    new_height = int(max_y - min_y)

    return new_width, new_height

def warp_texture(image, src_pts, dst_pts):
    """ Warps an image to fit into a quadrilateral using OpenCV. """
    h, w = image.shape[:2]

    src_pts = np.array(src_pts, dtype=np.float32)
    dst_pts = np.array(dst_pts, dtype=np.float32)

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    Projectivedst = cv2.warpPerspective(image, M, get_warped_image_size(M, w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))

    # Convert to Pygame surface
    warped_surface = pygame.surfarray.make_surface(cv2.cvtColor(Projectivedst, cv2.COLOR_BGR2RGB))
    warped_surface = pygame.transform.rotate(warped_surface, -90)
    warped_surface.set_colorkey((0, 0, 0))
    return warped_surface

def rotate_point(px, py, pz, ax, ay, az):
    """ Rotates a point (px, py, pz) around the given angles (ax, ay, az). """
    # Convert degrees to radians
    ax, ay, az = math.radians(ax), math.radians(ay), math.radians(az)

    # Rotate around X-axis
    y, z = py * math.cos(ax) - pz * math.sin(ax), py * math.sin(ax) + pz * math.cos(ax)
    py, pz = y, z

    # Rotate around Y-axis
    x, z = px * math.cos(ay) + pz * math.sin(ay), -px * math.sin(ay) + pz * math.cos(ay)
    px, pz = x, z

    # Rotate around Z-axis
    x, y = px * math.cos(az) - py * math.sin(az), px * math.sin(az) + py * math.cos(az)

    return x, y, pz


def project_point(px, py, pz, width, height):
    """ Projects a 3D point onto the 2D screen. """
    scale = 500 / (pz + 500)  # Simple perspective projection
    x2d = int(width / 2 + px * scale)
    y2d = int(height / 2 - py * scale)
    return x2d, y2d, pz


def draw_cuboid(surface, img, cuboid_width, cuboid_height, cuboid_depth, angle_x, angle_y, angle_z, dx=0, dy=0):
    """ Draws the 3D cuboid onto a given surface. """
    half_w, half_h, half_d = cuboid_width / 2, cuboid_height / 2, cuboid_depth / 2

    # Define 8 vertices
    vertices = [
        (-half_w, -half_h, -half_d), (half_w, -half_h, -half_d), (half_w, half_h, -half_d), (-half_w, half_h, -half_d),
        (-half_w, -half_h, half_d), (half_w, -half_h, half_d), (half_w, half_h, half_d), (-half_w, half_h, half_d)
    ]

    # Rotate & project
    projected = [project_point(*rotate_point(x, y, z, angle_x + 180, angle_y, angle_z), surface.get_width(), surface.get_height()) for x, y, z in vertices]

    # Define faces (with depth sorting)
    faces = [
        (projected[0], projected[1], projected[2], projected[3], FR4,
         sum(v[2] for v in [projected[0], projected[1], projected[2], projected[3]]) / 4),  # Back
        (projected[4], projected[5], projected[6], projected[7], WHITE,
        sum(v[2] for v in [projected[4], projected[5], projected[6], projected[7]]) / 4),
        (projected[0], projected[1], projected[5], projected[4], COPPER,
         sum(v[2] for v in [projected[0], projected[1], projected[5], projected[4]]) / 4),  # Side 1 (Copper/FR4)
        (projected[2], projected[3], projected[7], projected[6], COPPER,
         sum(v[2] for v in [projected[2], projected[3], projected[7], projected[6]]) / 4),  # Side 2 (Copper/FR4)
        (projected[1], projected[2], projected[6], projected[5], COPPER,
         sum(v[2] for v in [projected[1], projected[2], projected[6], projected[5]]) / 4),  # Side 3 (Copper/FR4)
        (projected[0], projected[3], projected[7], projected[4], COPPER,
         sum(v[2] for v in [projected[0], projected[3], projected[7], projected[4]]) / 4),  # Side 4 (Copper/FR4)
    ]

    # Sort faces by depth (draw furthest first)
    faces.sort(key=lambda f: f[5], reverse=True)

    # Draw faces
    for f in faces:
        face_points = [f[0][:2], f[1][:2], f[2][:2], f[3][:2]]
        pygame.draw.polygon(surface, f[4], [(x + dx, y + dy) for x, y in face_points])


    # Draw top face with texture last
    is_pcb_face_showing = faces[-1][4] == WHITE or faces[-2][4] == WHITE or faces[-3][4] == WHITE

    if is_pcb_face_showing:  # if is pcb face:
        top_vertices = [projected[4], projected[5], projected[6], projected[7]]
        top_points = [(v[0], v[1]) for v in top_vertices]

        min_x, min_y = min(top_points, key=lambda p: p[0])[0], min(top_points, key=lambda p: p[1])[1]
        tp_translated = [(x - min_x, y - min_y) for (x, y) in top_points]

        # Transform texture to match projection
        warped_texture = warp_texture(img,
                    [(0, 0), (cuboid_width, 0), (cuboid_width, cuboid_height), (0, cuboid_height)],
                            [tp_translated[2], tp_translated[3], tp_translated[0], tp_translated[1]])

        #warped_texture = pygame.transform.rotate(warped_texture, 180)
        warped_texture = pygame.transform.flip(warped_texture, True, False)
        surface.blit(warped_texture, (min_x + dx, min_y + dy))



def load_texture(path):
    return cv2.flip(cv2.imread(path), -1)

if __name__ == "__main__":
    pygame.init()

    cuboid_width = 488
    cuboid_height = 326
    cuboid_depth = 50

    # Screen settings
    WIDTH, HEIGHT = 1920, 1080
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    # Load top texture
    top_texture = load_texture("demo_texture.png")

    # Main loop
    running = True
    while running:
        screen.fill((30, 30, 30))  # Background color

        draw_cuboid(screen, top_texture, angle_x, angle_y, angle_z)

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    pygame.quit()