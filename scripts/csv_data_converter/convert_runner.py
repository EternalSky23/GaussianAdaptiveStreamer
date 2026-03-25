import os
import argparse
from csv_to_json import csv_to_json

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("scene_name")
    parser.add_argument("--width", type=int, required=True, help="Original image width (e.g., 1297). This is required.")
    parser.add_argument("--height", type=int, required=True, help="Original image height (e.g., 840). This is required.")
    
    args = parser.parse_args()

    input_dir = os.path.join(args.folder, args.scene_name)
    output_dir = f"output/{args.scene_name}"
    os.makedirs(output_dir, exist_ok=True)
    for file in os.listdir(input_dir):
        filename, ext = os.path.splitext(file)
        output_flie = f"out_{filename}.json"
        if ext != ".csv": continue

        csv_to_json(os.path.join(input_dir, file), os.path.join(output_dir, output_flie), args.width, args.height)