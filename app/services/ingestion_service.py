import json
import asyncio
import os
from app.core.database import db
from app.core.config import settings
import logging
import pandas as pd
from app.scripts.process_graph import process_logic, get_context

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self):
        try:
            mapping_path = os.path.join(settings.DATA_DIR, 'Biology_Mapping_Rules.xlsx')
            cat_path = os.path.join(settings.DATA_DIR, 'ai2d', 'categories.json')

            self.mapping_df = pd.read_excel(mapping_path)
            with open(cat_path, 'r', encoding='utf-8') as f:
                self.categories = json.load(f)
        except Exception as e:
            logger.error(f"Init warning: {e}")
            self.mapping_df = pd.DataFrame()
            self.categories = {}

    async def process_upload(self, raw_json_content: dict, image_id: str, rst_content: dict = None):
        # Chuẩn hóa dữ liệu đầu vào
        std_data = self._standardize_wrapper(raw_json_content, image_id)

        # Xác định Category
        target_category = raw_json_content.get("category")
        lookup_categories = self.categories.copy()
        if target_category:
            lookup_categories[image_id] = target_category

        context = get_context(image_id, lookup_categories, self.mapping_df)

        if not context:
            logger.warning(f"Bỏ qua {image_id}: Category không tìm thấy.")
            return {"status": "skipped", "reason": "Category not allowed"}

        # Xây dựng cấu trúc đồ thị (Nodes & Edges)
        nodes, edges = process_logic(std_data, rst_content, context)

        # Sinh mô tả dựa trên cấu trúc đồ thị
        description = self._generate_description(nodes, edges, context)

        # Tổng hợp dữ liệu cuối cùng
        final_payload = {
            "id": image_id,
            "imageUrl": f"{settings.R2_BASE_URL}/ai2d/raw/{image_id}",
            "meta": context,
            "raw": std_data["visual_objects"],
            "graph": {
                "nodes": nodes,
                "edges": edges
            },
            "description": description
        }

        # Thực hiện nạp dữ liệu song song vào 3 Database
        await asyncio.gather(
            self._ingest_to_mongo(final_payload),
            self._ingest_to_postgres(final_payload),
            self._ingest_to_neo4j(final_payload)
        )

        return {"status": "success", "id": image_id}

    def _generate_description(self, nodes, edges, context):
        cat = context['category']
        node_map = {n['uid']: n['name'] for n in nodes}

        if cat == 'lifeCycles':
            desc = "Vòng đời phát triển qua các giai đoạn: "
        elif cat == 'foodChainsWebs':
            desc = "Mối quan hệ dinh dưỡng trong hệ sinh thái: "
        else:
            desc = f"Quy trình {cat} mô tả: "

        relations = []
        for e in edges:
            src = node_map.get(e['source'], "Unknown")
            tgt = node_map.get(e['target'], "Unknown")
            relations.append(f"{src} -> {tgt}")

        if not relations:
            names = [n['name'] for n in nodes if len(n['name']) > 1]
            return f"{desc} các thành phần gồm {', '.join(names)}."

        return desc + ", ".join(relations)

    def _standardize_wrapper(self, raw_data, image_id):
        if 'visual_objects' in raw_data:
            return {
                "id": image_id,
                "visual_objects": raw_data['visual_objects'],
                "relationships": raw_data.get('relationships', [])
            }

        visual_objects = {"blobs": {}, "texts": [], "arrows": {}}

        # 1. Xử lý Blobs (Vùng đối tượng)
        blobs = raw_data.get('blobs', {})
        for k, v in blobs.items():
            visual_objects['blobs'][k] = {"id": k, "bbox": v.get('bbox', [0, 0, 0, 0])}
            if 'polygon' in v:
                poly = v['polygon']
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                # Tính toán Bbox [x, y, w, h] từ danh sách các điểm polygon
                visual_objects['blobs'][k]['bbox'] = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]

        # 2. Xử lý Texts (Văn bản)
        texts = raw_data.get('text', {})
        for k, v in texts.items():
            visual_objects['texts'].append({
                "id": k,
                "content": v.get('value', ''),
                "bbox": v.get('rectangle', [0, 0, 0, 0])
            })

        # 3. Xử lý Arrows (Mũi tên chỉ hướng)
        arrows = raw_data.get('arrows', {})
        for k, v in arrows.items():
            visual_objects['arrows'][k] = {"id": k, "bbox": v.get('bbox', [0, 0, 0, 0])}
            if 'polygon' in v:
                poly = v['polygon']
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                visual_objects['arrows'][k]['bbox'] = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]

        return {
            "id": image_id,
            "visual_objects": visual_objects,
            "relationships": raw_data.get('relationships', [])
        }

    async def _ingest_to_mongo(self, data):
        try:
            await db.mongo_db["diagrams_inventory"].replace_one(
                {"id": data["id"]},
                data,
                upsert=True
            )
        except Exception as e:
            logger.error(f"Mongo error: {e}")

    async def _ingest_to_postgres(self, data):
        conn = None
        try:
            conn = db.get_postgres_conn()
            cur = conn.cursor()
            query = """
                    INSERT INTO diagram_captions (diagram_id, caption, description, category)
                    VALUES (%s, %s, %s, %s) ON CONFLICT (diagram_id) DO 
                    UPDATE SET
                        caption=EXCLUDED.caption, description=EXCLUDED.description, category=EXCLUDED.category;
                    """
            cur.execute(query, (
                data['id'],
                f"{data['meta']['domain']} - {data['meta']['category']}",
                data['description'],
                data['meta']['category']
            ))
            conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Postgres error: {e}")

    async def _ingest_to_neo4j(self, data):
        if not db.neo4j_driver: return
        try:
            with db.neo4j_driver.session() as session:
                query = """
                MERGE (root:KnowledgeBase {name: "AI2D System"})
                MERGE (dom:StemDomain {name: $domain})
                MERGE (dom)-[:BELONGS_TO_KB]->(root)
                MERGE (cat:Category {name: $category})
                MERGE (cat)-[:IN_DOMAIN]->(dom)
                MERGE (d:Diagram {id: $id})
                MERGE (d)-[:BELONGS_TO]->(cat)

                WITH d
                UNWIND $nodes AS n_dat
                MERGE (n:Entity {uid: n_dat.uid})
                SET n.name = n_dat.name, n.type = n_dat.type
                MERGE (d)-[:CONTAINS]->(n)
                MERGE (c:Concept {name: n_dat.name})
                MERGE (n)-[:REPRESENTS]->(c)

                WITH d
                UNWIND $edges AS e_dat
                MATCH (src:Entity {uid: e_dat.source})
                MATCH (tgt:Entity {uid: e_dat.target})
                MERGE (src)-[:LINKED_TO {via: e_dat.relation}]->(tgt)
                """
                session.run(query,
                            id=data["id"], domain=data["meta"]["domain"], category=data["meta"]["category"],
                            nodes=data["graph"]["nodes"], edges=data["graph"]["edges"]
                            )
        except Exception as e:
            logger.error(f"Neo4j error: {e}")


ingestion_service = IngestionService()