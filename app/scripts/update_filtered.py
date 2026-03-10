import os
import json
from app.core.config import settings


def main():
    filter_file = os.path.join(settings.DATA_DIR, "filtered_ids.json")
    cat_file = os.path.join(settings.DATA_DIR, "ai2d", "categories.json")
    rst_dir = os.path.join(settings.DATA_DIR, "ai2d_rst")

    with open(cat_file, 'r', encoding='utf-8') as f:
        categories = json.load(f)

    with open(filter_file, 'r', encoding='utf-8') as f:
        current_ids = json.load(f)

    allowed_categories = ["foodChainsWebs", "lifeCycles"]
    new_ids = []

    for img_id in current_ids:
        if categories.get(img_id) not in allowed_categories:
            continue

        rst_path = os.path.join(rst_dir, f"{img_id}.json")
        if os.path.exists(rst_path):
            new_ids.append(img_id)

    with open(filter_file, 'w', encoding='utf-8') as f:
        json.dump(new_ids, f)

    print(f"So luong ID ban dau: {len(current_ids)}")
    print(f"So luong ID giu lai: {len(new_ids)}")


if __name__ == "__main__":
    main()