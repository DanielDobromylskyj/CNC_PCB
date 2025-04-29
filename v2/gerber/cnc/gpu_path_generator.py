import pyopencl as cl
import numpy as np
from PIL import Image


platforms = cl.get_platforms()
devices = platforms[0].get_devices()
context = cl.Context(devices)
queue = cl.CommandQueue(context, devices[0])


def create_outline(img, outline_width):
    img_copy = img.convert("1")

    width, height = img_copy.size

    img_data = np.array(img_copy, dtype=np.uint8)
    outline_data = np.ones_like(img_data, dtype=np.uint8)

    img1_buffer = cl.Buffer(context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=img_data)
    img2_buffer = cl.Buffer(context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=img_data)
    outline_buffer = cl.Buffer(context, cl.mem_flags.READ_WRITE, outline_data.nbytes, hostbuf=None)


    program_src = """
__kernel void create_outline(
    __global const uchar *img,
    __global uchar *img_next,
    __global uchar *outline,
    const int width,
    const int height,
    const int outline_width) 
{
    int x = get_global_id(0);
    int y = get_global_id(1);

    if (x >= width || y >= height) return;

    const int idx = y * width + x;

    const int positions[8][2] = {
        {-1, 0}, {1, 0}, {0, -1}, {0, 1},
        {1, 1}, {1, -1}, {-1, -1}, {-1, 1}
    };

    if (img[idx] == 1) {
        for (uchar i = 0; i < 8; i++) {
            int nx = x + positions[i][0];
            int ny = y + positions[i][1];
            if (nx >= 0 && ny >= 0 && nx < width && ny < height) {
                if (img[ny * width + nx] == 0) {
                    outline[idx] = 0;
                    img_next[idx] = 0;
                    return;
                }
            }
        }
    }

    outline[idx] = 1;
}

    """
    program = cl.Program(context, program_src).build()

    for i in range(outline_width):
        program.create_outline(queue, (width, height), None, img1_buffer, img2_buffer, outline_buffer, np.int32(width),
                               np.int32(height), np.int32(i))

        cl.enqueue_copy(queue, img1_buffer, img2_buffer)

    cl.enqueue_copy(queue, outline_data, outline_buffer).wait()
    outline_copy = Image.fromarray(outline_data.astype(np.uint8) * 255)

    return outline_copy
