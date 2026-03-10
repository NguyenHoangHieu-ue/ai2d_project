import json
import os
from app.core.config import settings

INPUT_DIR = os.path.join(settings.DATA_DIR, "ai2d", "annotations")
OUTPUT_DIR = os.path.join(settings.DATA_DIR, "02_standardized")
FILTER_FILE = os.path.join(settings.DATA_DIR, "filtered_ids.json")

def standardize_wrapper(raw_data, image_id):
    visual_objects = {"blobs": {}, "texts": [], "arrows": {}}

    for k, v in raw_data.get("blobs", {}).items():
        poly = v.get("polygon", [])
        if poly:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            bbox = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
        else:
            bbox = [0, 0, 0, 0]
        visual_objects["blobs"][k] = {"id": k, "bbox": bbox}

    for k, v in raw_data.get("text", {}).items():
        visual_objects["texts"].append({
            "id": k,
            "content": v.get("value", ""),
            "bbox": v.get("rectangle", [0, 0, 0, 0])
        })

    for k, v in raw_data.get("arrows", {}).items():
        poly = v.get("polygon", [])
        if poly:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            bbox = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
        else:
            bbox = [0, 0, 0, 0]
        visual_objects["arrows"][k] = {"id": k, "bbox": bbox}

    connections = []
    for rel in raw_data.get("relationships", {}).values():
        cat = rel.get("category")
        if cat == "interObjectLinkage":
            connections.append({
                "type": "connection",
                "from": rel.get("origin"),
                "to": rel.get("destination"),
                "via": rel.get("connector")
            })
        elif cat == "intraObjectLabel":
            connections.append({
                "type": "labeling",
                "label": rel.get("origin"),
                "object": rel.get("destination")
            })

    return {"id": image_id, "visual_objects": visual_objects, "relationships": connections}

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if not os.path.exists(FILTER_FILE):
        print("Chua co file loc. Hay chay script 01 truoc!")
        return

    with open(FILTER_FILE, 'r') as f:
        valid_ids = json.load(f)

    print(f"Dang chuan hoa {len(valid_ids)} file theo danh sach loc...")

    for image_id in valid_ids:
        filename = f"{image_id}.json"
        input_path = os.path.join(INPUT_DIR, filename)

        if not os.path.exists(input_path):
            print(f"Canh bao: ID {image_id} thieu file annotation goc.")
            continue

        with open(input_path, 'r', encoding='utf-8') as infile:
            raw = json.load(infile)

        std = standardize_wrapper(raw, image_id)
        output_path = os.path.join(OUTPUT_DIR, filename)

        with open(output_path, 'w', encoding='utf-8') as outfile:
            json.dump(std, outfile, indent=2)

    print("Chuan hoa hoan tat.")

if __name__ == "__main__":
    main()