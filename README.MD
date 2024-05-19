# DungeonScrawl to UVTT

Command line tool to convert a [DungeonScrawl](https://app.dungeonscrawl.com/) file to the more generic and widely supported UVTT (Universal Virtual Table Top) file format.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Support](#support)
- [License](#license)

## Installation

This script only requires that you have [Python](https://www.python.org/) installed. Once you've done that you can run this script like you can run any other Python script. It does not have additional dependencies.

## Usage

There are a few things to keep in mind to make this work. Lets go through them quickly.

### 1 - Drawing

Draw your map in DungeonScrawl while keeping the following limitations in mind. Perform all your drawing on the original dungeon layer you get when opening a new file. No extra layers or unpacking of layers for custom styling. Doors will be recognized and converted when drawn with the door tool only.

 ### 2 - Mark the origin
 
 Before exporting to an image first draw a little corner with the wall tool marking the top left of the area you wish to export. Use snap and make certain the corner point is on a grid intersection. 
 
 ### 3 - Save map and export image
 
 When exporting to a `.png` make certain the exported area's top left corner matches the corner you've drawn as shown in Fig 1. If you do not do this your `.dd2vtt` file will have a weird offset.

<p align="center">
  <img src="./images/export_area_with_top_left_mark.png" alt="Top left export area with mark">
  <br>
  <em>Fig 1: Top left export area with mark</em>
</p>

The exported area should encompass full tiles only, no half or quarter tiles. If you change the value of `px per cell` from the default of `70`, make a note of it since you will need it later.

Now save your dscrawl map from the file menu. Place both the `.png` and the `.ds` files in the same folder as the `dscrawl_to_uvtt.py` script.

### 4 - Convert to UVVT

You call the tool with the following arguments

#### Positional arguments (required)
- DungeonScrawl file to convert.
- Map width (in tiles)
- Map height (in tiles)

#### Optional arguments
- `-t, --tile_size`: Single tile size (in pixels)
- `-i, --image`: The image file you exported from DungeonScrawl
- `-h, --help`: Displays the help message and usage instructions.

#### Example

Imagine your dungeonscrawl file is `dungeon_map.ds` and the exported image file is `dungeon_map_20x32.png`. You have not changed the `px per cell` value when exporting from its default value of `70`. You've placed these files in the same folder as the `dscrawl_to_uvtt.py` script.

Now type the following command in the terminal:

`python dscrawl_to_uvtt.py dungeon_map.ds 20 32 -i dungeon_map_20x32.png`

## Support

This tool is written for personal use. I only share it because I feel it could be useful to others but will not provide support.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.MD) file for details.
