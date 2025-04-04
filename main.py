import os
import json
from mcrcon import MCRcon

from image_processing import parse_list_response, process_image_depthmap_and_get_commands
from send_commands import send_commands

def main():
    # Define base directories and file paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_DIR = os.path.join(BASE_DIR, "database")
    IMG_DIR = os.path.join(BASE_DIR, "images")

    rgb_json_path = os.path.join(DB_DIR, "rgb_values.json")
    manual_json_path = os.path.join(DB_DIR, "manual.json")
    image_path = os.path.join(IMG_DIR, "image.png")
    
    # Check required JSON file
    if not os.path.exists(rgb_json_path):
        print(f"Error: {rgb_json_path} does not exist!")
        return

    if not os.path.exists(manual_json_path):
        print(f"Warning: {manual_json_path} does not exist!")
        print("Continuing without manual.json data.")
    else:
        with open(manual_json_path, "r", encoding="utf-8") as f:
            manual_data = json.load(f)

    # Set Minecraft RCON connection parameters
    host = "localhost"
    port = 25575
    password = "" # PASSWORD HERE
    player_name = "" # PLAYER NAME HERE

    # Check for empty RCON credentials
    if not password or not player_name:
        print("Error: Both password and player_name must be provided for RCON connection!")
        return
    
    # Connect to Minecraft to get player position and rotation.
    print("Connecting to Minecraft server via RCON to retrieve player data...")
    with MCRcon(host, password, port=port) as mcr:
        pos_response = mcr.command(f"data get entity {player_name} Pos")
        rot_response = mcr.command(f"data get entity {player_name} Rotation")
        pos = parse_list_response(pos_response)
        rot = parse_list_response(rot_response)
        if pos is None or rot is None:
            print("Error: Failed to parse player position or rotation. Check RCON setup & player name.")
            return
        player_info = {"pos": pos, "rot": rot}
        print(f"Player position: {pos}")
        print(f"Player rotation: {rot}")

    # Process the image to get the list of setblock commands
    commands = process_image_depthmap_and_get_commands(image_path, rgb_json_path, player_info)
    
    # Send the commands to Minecraft via RCON
    send_commands(commands, host, port, password)

if __name__ == "__main__":
    main()
