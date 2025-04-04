Below is an example of a clean, well-organized Markdown document for your project. You can copy and paste this into your project’s README.md file.

---

# Minecraft Anamorphic Project

This project leverages Python to convert images into Minecraft `setblock` commands—creating a 3D anamorphic display in your Minecraft world. By processing an image to generate a depth map and mapping pixel colors to Minecraft blocks, the project builds an immersive structure using a Minecraft RCON connection.

![Castle Perspective](demonstration/Castle_Perspective.gif)  

## Table of Contents
- [Features](#features)
- [File Structure](#file-structure)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [Code Overview](#code-overview)
  - [main.py](#mainpy)
  - [image_processing.py](#image_processingpy)
  - [send_commands.py](#send_commandspy)
- [Demonstration](#demonstration)
- [Credits](#credits)
- [License](#license)

## Features
- **Image to Minecraft Blocks:** Converts a given image into a series of Minecraft `setblock` commands.
- **Depth Map Generation:** Processes the image into a depth map, providing a 3D perspective.
- **Color Mapping:** Maps image pixel colors to the closest matching Minecraft block using an RGB mapping.
- **Efficient Command Sending:** Uses a connection pool with RCON to efficiently send commands to your Minecraft server.
- **Demonstrations:** Includes GIFs to showcase the project in action.

## File Structure
```
database/
  manual.json
  rgb_values.json
images/
  castle.png
  image.png
  starter_image.png
image_processing.py
main.py
send_commands.py
```

## Setup and Installation
1. **Prerequisites:**
   - Python 3.x
   - Libraries: `Pillow`, `numpy`, `mcrcon`
   - A running Minecraft server with RCON enabled

2. **Installation:**
   - Clone this repository.
   - Install the required libraries:
     ```bash
     pip install Pillow numpy mcrcon
     ```
   - Configure your Minecraft server’s RCON settings (host, port, and password).

3. **Database Files:**
   - You can pick or modify your own `rgb_values.json` (for block-to-RGB mapping) and optionally `manual.json` in the `database/` directory. The default setup is a posterization mapping from RGB colors to full and non-transparent blocks.

## Usage
1. Place your desired image (e.g., `image.png`) in the `images/` folder.
2. Update the RCON connection parameters in `main.py` (host, port, password).
3. Run the project:
   ```bash
   python main.py
   ```
4. The project will:
   - Connect to the Minecraft server via RCON.
   - Retrieve the player’s position and rotation.
   - Process the image to generate `setblock` commands.
   - Send the commands to build the image within Minecraft.

## Code Overview

### main.py
- **Purpose:** Acts as the entry point.
- **Functionality:**
  - Sets up directories and validates the presence of necessary JSON files.
  - Connects to the Minecraft server to retrieve player data (position and rotation).
  - Processes the image to generate block placement commands.
  - Sends the commands to Minecraft via RCON.

### image_processing.py
- **Purpose:** Handles image processing.
- **Key Functions:**
  - `parse_list_response`: Extracts numeric values from RCON responses.
  - `load_rgb_data` & `find_closest_block`: Load RGB mappings and determine the closest Minecraft block for a given color.
  - `get_depth_map`: Generates a grayscale depth map from an image.
  - `process_image_depthmap_and_get_commands`: Resizes the image, creates a depth map, and computes 3D block positions based on player perspective.

### send_commands.py
- **Purpose:** Manages the sending of commands.
- **Key Components:**
  - `RCONConnectionPool`: Establishes a pool of RCON connections.
  - `send_commands`: Sends the list of `setblock` commands concurrently to the Minecraft server.

## Demonstration

Below are some demonstration GIFs showcasing the project in action:

 - A castle image with lots of noise and details, can result in a completely chaotic side view.
![Castle Construction](demonstration/Castle_Construction.gif)  
![Castle Perspective](demonstration/Castle_Perspective.gif)  

 - A stylized flag with large portions being solid colors, to show the clear depth separation. 
![Flag Construction](demonstration/Flag_Construction.gif)  
![Flag Perspective](demonstration/Flag_Perspective.gif)  

## Credits
This project was inspired by [this video](https://youtu.be/RUBg41KUs2I), which sparked the idea of automating the process of creating 3D anamorphic displays in Minecraft.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.