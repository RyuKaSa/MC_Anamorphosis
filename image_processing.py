import math
import re
import json
from PIL import Image
import numpy as np

##############################################################################
#                           HELPER FUNCTIONS
##############################################################################

def parse_list_response(response):
    """
    Extracts a numeric list from a response string like:
      'Pos has the following properties: [123.0, 64.0, -12.0]'
    and returns it as a list of floats.
    """
    match = re.search(r'\[([^\]]+)\]', response)
    if not match:
        return None
    data = match.group(1)
    parts = data.split(',')
    try:
        values = [float(re.sub(r'[^\d\.\-+eE]', '', p)) for p in parts]
    except ValueError:
        return None
    return values

def dot(u, v):
    return u[0]*v[0] + u[1]*v[1] + u[2]*v[2]

def cross(u, v):
    return (u[1]*v[2] - u[2]*v[1],
            u[2]*v[0] - u[0]*v[2],
            u[0]*v[1] - u[1]*v[0])

def norm(u):
    return math.sqrt(dot(u, u))

def normalize(u):
    n = norm(u)
    if n == 0:
        return (0, 0, 0)
    return (u[0]/n, u[1]/n, u[2]/n)

##############################################################################
#                   COLOR MAPPING FUNCTIONS
##############################################################################

def load_rgb_data(rgb_json_path):
    """
    Loads the block-to-RGB mapping from the JSON file.
    Returns a dict: block_id -> (R, G, B)
    """
    with open(rgb_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    block_rgb_map = {}
    for block_id, rgb_list in data.items():
        block_rgb_map[block_id] = tuple(rgb_list)
    return block_rgb_map

def find_closest_block(r, g, b, block_rgb_map):
    """
    Given an (r, g, b) color, find the block in block_rgb_map
    whose color is closest by Euclidean distance.
    """
    closest_block = None
    closest_distance_sq = float('inf')
    for block_id, (br, bg, bb) in block_rgb_map.items():
        dist_sq = (r - br)**2 + (g - bg)**2 + (b - bb)**2
        if dist_sq < closest_distance_sq:
            closest_distance_sq = dist_sq
            closest_block = block_id
    return closest_block

##############################################################################
#                   PERSPECTIVE PLANE GENERATION
##############################################################################

def generate_plane_commands(distance, base_distance, plane_width, plane_height, pixel_scale,
                              eye_pos, look_vector, right_vector, true_up_vector,
                              block_id="minecraft:stone", offset_right=0):
    """
    Generates setblock commands for a rectangular plane (grid) that is perpendicular
    to the player's view (camera). The plane's center is placed at a specified 'distance'
    along the player's look vector (starting at the player's eye position) and then shifted
    laterally along the right vector by an effective offset (which is perspective-scaled).

    Returns a list of setblock commands.
    """
    scale_factor = distance / base_distance
    effective_offset = offset_right * scale_factor

    plane_center = (
        eye_pos[0] + look_vector[0] * distance + right_vector[0] * effective_offset,
        eye_pos[1] + look_vector[1] * distance + right_vector[1] * effective_offset,
        eye_pos[2] + look_vector[2] * distance + right_vector[2] * effective_offset
    )
    
    half_width = (plane_width * pixel_scale * scale_factor) / 2.0
    half_height = (plane_height * pixel_scale * scale_factor) / 2.0

    top_left = (
        plane_center[0] - half_width * right_vector[0] + half_height * true_up_vector[0],
        plane_center[1] - half_width * right_vector[1] + half_height * true_up_vector[1],
        plane_center[2] - half_width * right_vector[2] + half_height * true_up_vector[2]
    )

    commands = []
    for row in range(plane_height):
        for col in range(plane_width):
            offset_x = (col * pixel_scale * scale_factor) * right_vector[0] - (row * pixel_scale * scale_factor) * true_up_vector[0]
            offset_y = (col * pixel_scale * scale_factor) * right_vector[1] - (row * pixel_scale * scale_factor) * true_up_vector[1]
            offset_z = (col * pixel_scale * scale_factor) * right_vector[2] - (row * pixel_scale * scale_factor) * true_up_vector[2]

            block_pos = (
                top_left[0] + offset_x,
                top_left[1] + offset_y,
                top_left[2] + offset_z
            )
            bx = int(round(block_pos[0]))
            by = int(round(block_pos[1]))
            bz = int(round(block_pos[2]))
            cmd = f"setblock {bx} {by} {bz} {block_id}"
            commands.append(cmd)
    return commands

##############################################################################
#            DEPTH MAP GENERATION AND IMAGE PROCESSING
##############################################################################

def get_depth_map(image_path, min_distance, max_distance):
    """
    Create a simple depth map from an image by converting it to grayscale.
    Each pixel value (0-255) is normalized and mapped to a distance in the range
    [min_distance, max_distance], but with depth flipped so that dark pixels are farther.
    """
    im = Image.open(image_path).convert("L")
    arr = np.array(im, dtype=np.float32)
    normalized = arr / 255.0
    # depth: white is min_distance, black is max_distance.
    depth_map = max_distance - normalized * (max_distance - min_distance)
    return depth_map

def process_image_depthmap_and_get_commands(image_path, rgb_json_path, player_info,
                                            min_distance=60.0, max_distance=180.0,
                                            pixel_scale=1, output_width=400, output_height=None):
    """
    Processes an image by first resizing it to the desired output dimensions and then generating
    a block placement command for each pixel. The image is converted to a depth map so that each pixel 
    is assigned a (flipped) distance. For each pixel, the block's world position is computed using the player's 
    perspective, and the pixel color is mapped to the closest Minecraft block based on an RGB-to-block mapping.
    
    Additionally, the alpha channel is used:
      - If a pixel's alpha is below 50% (i.e. alpha < 128), it is skipped.
      - Otherwise, the pixel is used.
    
    Also, for pixels whose computed distance is in the farthest 20% of the range,
    the block is drawn double in width and height (i.e. a 2×2 block square is generated).
    
    Parameters:
      - output_width: The desired width (in pixels) of the resized image.
      - output_height: The desired height (in pixels) of the resized image. If None, the aspect ratio
        of the original image is maintained.
    """
    # Load the block RGB mapping.
    block_rgb_map = load_rgb_data(rgb_json_path)
    
    # Open the original image in RGBA.
    orig_im = Image.open(image_path).convert("RGBA")
    orig_width, orig_height = orig_im.size
    if output_height is None:
        output_height = int(output_width * (orig_height / orig_width))
    
    # Resize the image to control the number of commands generated.
    im = orig_im.resize((output_width, output_height), Image.LANCZOS)
    
    # Create the flipped depth map from the resized image.
    im_gray = im.convert("L")
    arr = np.array(im_gray, dtype=np.float32)
    normalized = arr / 255.0
    depth_map = max_distance - normalized * (max_distance - min_distance)
    
    width, height = im.size
    pixel_data = im.load()  # Now returns RGBA tuples.
    
    # Compute the image center.
    center_x = width / 2.0
    center_y = height / 2.0
    
    # Compute the player's eye position.
    px, py, pz = player_info["pos"]
    eye_height = 1.62  # Typical Minecraft eye height.
    eye_pos = (px, py + eye_height, pz)
    
    # Compute the look vector from yaw and pitch.
    yaw, pitch = player_info["rot"]
    yaw_rad = math.radians(yaw)
    pitch_rad = math.radians(pitch)
    dx = -math.sin(yaw_rad) * math.cos(pitch_rad)
    dy = -math.sin(pitch_rad)
    dz = math.cos(yaw_rad) * math.cos(pitch_rad)
    look_vector = (dx, dy, dz)
    
    # Compute the right and true-up vectors.
    approximate_up = (0, 1, 0)
    if abs(dot(look_vector, approximate_up)) > 0.99:
        approximate_up = (1, 0, 0)
    right_vector = normalize(cross(approximate_up, look_vector))
    true_up_vector = normalize(cross(look_vector, right_vector))
    
    base_distance = max_distance  # Reference for perspective scaling.
    commands = []
    
    # Define threshold: farthest 40% of the distance range.
    far_threshold = min_distance + 0.6 * (max_distance - min_distance)
    
    # Process each pixel.
    for row in range(height):
        for col in range(width):
            pixel = pixel_data[col, row]  # (R, G, B, A)
            alpha_val = pixel[3]
            # Skip pixels that are too transparent (alpha below 50%).
            if alpha_val < 128:
                continue
            
            # Use the pixel's RGB for block mapping.
            color = pixel[:3]
            block_id = find_closest_block(color[0], color[1], color[2], block_rgb_map)
            if block_id is None:
                block_id = "minecraft:stone"
            
            distance = float(depth_map[row, col])
            scale_factor = distance / base_distance
            
            # Invert left/right by multiplying by -1.
            norm_offset_right = -((col - center_x) / (width / 2)) * (output_width / 2) * scale_factor
            norm_offset_up = ((center_y - row) / (height / 2)) * (output_height / 2) * scale_factor
            
            block_pos = (
                eye_pos[0] + look_vector[0] * distance + right_vector[0] * norm_offset_right + true_up_vector[0] * norm_offset_up,
                eye_pos[1] + look_vector[1] * distance + right_vector[1] * norm_offset_right + true_up_vector[1] * norm_offset_up,
                eye_pos[2] + look_vector[2] * distance + right_vector[2] * norm_offset_right + true_up_vector[2] * norm_offset_up,
            )
            
            # If the pixel is in the farthest 20% of the depth range, double the block area.
            if distance >= far_threshold:
                delta_r = (pixel_scale * scale_factor * right_vector[0],
                           pixel_scale * scale_factor * right_vector[1],
                           pixel_scale * scale_factor * right_vector[2])
                delta_u = (pixel_scale * scale_factor * true_up_vector[0],
                           pixel_scale * scale_factor * true_up_vector[1],
                           pixel_scale * scale_factor * true_up_vector[2])
                
                positions = [
                    block_pos,
                    (block_pos[0] + delta_r[0], block_pos[1] + delta_r[1], block_pos[2] + delta_r[2]),
                    (block_pos[0] + delta_u[0], block_pos[1] + delta_u[1], block_pos[2] + delta_u[2]),
                    (block_pos[0] + delta_r[0] + delta_u[0], block_pos[1] + delta_r[1] + delta_u[1], block_pos[2] + delta_r[2] + delta_u[2])
                ]
                for pos in positions:
                    bx = int(round(pos[0]))
                    by = int(round(pos[1]))
                    bz = int(round(pos[2]))
                    cmd = f"setblock {bx} {by} {bz} {block_id}"
                    commands.append(cmd)
            else:
                bx = int(round(block_pos[0]))
                by = int(round(block_pos[1]))
                bz = int(round(block_pos[2]))
                cmd = f"setblock {bx} {by} {bz} {block_id}"
                commands.append(cmd)
    
    print(f"Generated {len(commands)} commands for image processing.")
    return commands
