import os
import pandas as pd
from app.core.config import settings

OUTPUT_FILE = os.path.join(settings.DATA_DIR, "Biology_Mapping_Rules.xlsx")

def main():
    print("Tao file Mapping...")

    data = [
        {
            "category": "foodChainsWebs",
            "stem_domain": "Biology",
            "node_label": "Organism",
            "description": "Sinh vat trong chuoi thuc an"
        },
        {
            "category": "lifeCycles",
            "stem_domain": "Biology",
            "node_label": "Stage",
            "description": "Giai doan phat trien"
        }
    ]

    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    df.to_excel(OUTPUT_FILE, index=False)
    print(f"Da tao: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()