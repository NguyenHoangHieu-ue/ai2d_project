import asyncio
import os
import json
from app.services.ingestion_service import ingestion_service
from app.core.database import db
from app.core.config import settings

STD_DIR = os.path.join(settings.DATA_DIR, "02_standardized")
RST_DIR = os.path.join(settings.DATA_DIR, "ai2d_rst")
FILTER_FILE = os.path.join(settings.DATA_DIR, "filtered_ids.json")

async def main():
    print("BAT DAU NAP DU LIEU...")

    if not os.path.exists(FILTER_FILE):
        print("Khong tim thay file loc ID")
        return

    with open(FILTER_FILE, 'r') as f:
        valid_ids = json.load(f)

    await db.connect()

    try:
        total = len(valid_ids)
        print(f"Tong so file: {total}")

        for i, image_id in enumerate(valid_ids):
            filename = f"{image_id}.json"
            std_path = os.path.join(STD_DIR, filename)
            rst_path = os.path.join(RST_DIR, filename)

            if not os.path.exists(std_path):
                print(f"Skip {image_id}: Thieu file Standardized")
                continue

            with open(std_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            rst_data = None
            if os.path.exists(rst_path):
                try:
                    with open(rst_path, 'r', encoding='utf-8') as f:
                        rst_data = json.load(f)
                except:
                    print(f"Loi doc RST {image_id}")

            await ingestion_service.process_upload(raw_data, image_id, rst_data)

            if (i+1) % 10 == 0:
                print(f"Tien do: {i+1}/{total}")

    finally:
        await db.close()
        print("HOAN TAT")

if __name__ == "__main__":
    asyncio.run(main())