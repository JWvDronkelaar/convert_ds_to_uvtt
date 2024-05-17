
import base64
import argparse
import json

from generic_functions import *
from door_functions import *

def dscrawl_to_uvtt(dscrawl_file_name, map_width, map_height, tile_size, image_file_name=None):
    """
    Converts a DScrawl file to a UVTT file format.

    Args:
        dscrawl_file_name (str): The name of the DScrawl file to convert.
        map_width (int): The width of the map in cells.
        map_height (int): The height of the map in cells.
        tile_size (int): The size of each tile in pixels.
        image_file_name (str, optional): The name of the image file to include in the UVTT file. Defaults to None.

    Returns:
        None
    """
    map_data = parse_map_data(dscrawl_file_name)
    geometry_ids = get_geometry_ids(map_data)

    polygons, polylines = extract_geometry(map_data, geometry_ids["walls"])

    obstruction_lines = convert_polygons(polygons) + convert_polylines(polylines)
     
    obstruction_lines = scale_and_offset_coordinates(obstruction_lines)

    portals = generate_portals(map_data, geometry_ids["doors"])

    map_dict = generate_map_dict(map_size=[map_width,map_height], cell_size=tile_size)
    map_dict["line_of_sight"] = obstruction_lines
    map_dict["portals"] = portals
    
    if image_file_name:
        with open(image_file_name, mode='rb') as file:
            image = file.read()    
        map_dict["image"] = base64.encodebytes(image).decode('utf-8')

    output_file_name = dscrawl_file_name[:-3] + ".dd2vtt"
    with open(output_file_name, 'w') as file:
        json.dump(map_dict, file, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provide information to create a .dd2vtt file.")
    parser.add_argument("dscrawl_file_name", type=str, help="Path to DungeonScrawl file.")
    parser.add_argument("map_width", type=int, help="Map width (in tiles).")
    parser.add_argument("map_height", type=int, help="Map height (in tiles).")
    parser.add_argument("tile_size", type=int, help="Singe tile size (in pizels).")
    parser.add_argument("--image", type=str, default=None, help="Path to image file.")
    args = parser.parse_args()

    dscrawl_to_uvtt(
        args.dscrawl_file_name, args.map_width, 
        args.map_height, args.tile_size, 
        image_file_name=args.image)
