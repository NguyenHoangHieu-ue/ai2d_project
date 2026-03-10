from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.core.database import db
from app.models.schemas import DiagramListResponse, DiagramDetailResponse, SearchResponse

router = APIRouter()

@router.get("/diagrams", response_model=DiagramListResponse)
async def get_diagrams(category: Optional[str] = Query(None, description="Loc theo chu de")):
    query = {}
    if category:
        query["meta.category"] = category

    cursor = db.mongo_db["diagrams_inventory"].find(query)
    items = []

    async for doc in cursor:
        items.append({
            "id": doc.get("id"),
            "image_url": doc.get("imageUrl"),
            "meta": {
                "category": doc.get("meta", {}).get("category"),
                "domain": doc.get("meta", {}).get("domain"),
                "description": doc.get("description")
            },
            "graph": doc.get("graph"),
            "raw_data": None
        })

    return {"total": len(items), "items": items}


@router.get("/diagrams/{diagram_id}", response_model=DiagramDetailResponse)
async def get_diagram_detail(diagram_id: str):
    doc = await db.mongo_db["diagrams_inventory"].find_one({"id": diagram_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Khong tim thay so do")

    return {
        "id": doc.get("id"),
        "image_url": doc.get("imageUrl"),
        "meta": {
            "category": doc.get("meta", {}).get("category"),
            "domain": doc.get("meta", {}).get("domain"),
            "description": doc.get("description")
        },
        "graph": doc.get("graph"),
        "raw_data": doc.get("raw")
    }


@router.get("/search/related", response_model=SearchResponse)
async def search_related(
        keyword: str = Query(..., description="Tu khoa tim kiem"),
        category: Optional[str] = Query(None, description="Loc theo chu de")
):
    query = {
        "$or": [
            {"graph.nodes.name": {"$regex": keyword, "$options": "i"}},
            {"description": {"$regex": keyword, "$options": "i"}}
        ]
    }

    if category:
        query["meta.category"] = category

    cursor = db.mongo_db["diagrams_inventory"].find(query)
    items = []

    async for doc in cursor:
        items.append({
            "id": doc.get("id"),
            "image_url": doc.get("imageUrl"),
            "meta": {
                "category": doc.get("meta", {}).get("category"),
                "domain": doc.get("meta", {}).get("domain"),
                "description": doc.get("description")
            }
        })

    return {"total": len(items), "items": items}


@router.get("/graph/global")
async def get_global_graph():
    if not db.neo4j_driver:
        raise HTTPException(status_code=500, detail="Neo4j khong hoat dong")

    nodes_dict = {}
    edges = []

    with db.neo4j_driver.session() as session:
        # 1. Tầng gốc (Root -> Domain -> Category)
        q1 = """
        MATCH (n)-[r]->(m)
        WHERE labels(n)[0] IN ['KnowledgeBase', 'StemDomain', 'Category']
          AND labels(m)[0] IN ['KnowledgeBase', 'StemDomain', 'Category']
        RETURN elementId(n) AS source_id, labels(n)[0] AS source_label, n.name AS source_name,
               elementId(m) AS target_id, labels(m)[0] AS target_label, m.name AS target_name,
               type(r) AS rel_type
        """

        # 2. Category -> Diagram (Giới hạn 15 sơ đồ để không lag)
        q2 = """
        MATCH (cat:Category)<-[:BELONGS_TO]-(d:Diagram) WITH cat, d LIMIT 15
        RETURN elementId(cat) AS source_id, labels(cat)[0] AS source_label, cat.name AS source_name,
               elementId(d) AS target_id, labels(d)[0] AS target_label, d.id AS target_name,
               'HAS_DIAGRAM' AS rel_type
        """

        # 3. Diagram -> Entity (Nối sơ đồ với các thành phần của nó)
        q3 = """
        MATCH (cat:Category)<-[:BELONGS_TO]-(d:Diagram) WITH d LIMIT 15
        MATCH (d)-[:CONTAINS]->(e:Entity)
        RETURN elementId(d) AS source_id, labels(d)[0] AS source_label, d.id AS source_name,
               elementId(e) AS target_id, labels(e)[0] AS target_label, e.name AS target_name,
               'CONTAINS' AS rel_type
        """

        # 4. Entity -> Entity (Vẽ câu chuyện: Egg -> Larva -> Pupa...)
        q4 = """
        MATCH (cat:Category)<-[:BELONGS_TO]-(d:Diagram) WITH d LIMIT 15
        MATCH (d)-[:CONTAINS]->(e1:Entity)-[r]->(e2:Entity)<-[:CONTAINS]-(d)
        RETURN elementId(e1) AS source_id, labels(e1)[0] AS source_label, e1.name AS source_name,
               elementId(e2) AS target_id, labels(e2)[0] AS target_label, e2.name AS target_name,
               type(r) AS rel_type
        """

        for query in [q1, q2, q3, q4]:
            result = session.run(query)
            for record in result:
                s_id = record["source_id"]
                t_id = record["target_id"]

                if s_id not in nodes_dict:
                    nodes_dict[s_id] = {
                        "id": s_id, "label": record["source_label"], "name": record["source_name"]
                    }
                if t_id not in nodes_dict:
                    nodes_dict[t_id] = {
                        "id": t_id, "label": record["target_label"], "name": record["target_name"]
                    }
                edges.append({
                    "source": s_id, "target": t_id, "type": record["rel_type"]
                })

    return {"nodes": list(nodes_dict.values()), "edges": edges}


@router.get("/graph/category/{category_name}")
async def get_category_graph(category_name: str):
    if not db.neo4j_driver:
        raise HTTPException(status_code=500, detail="Neo4j khong hoat dong")

    nodes_dict = {}
    edges = []

    with db.neo4j_driver.session() as session:
        # 1. Category -> Diagram
        q1 = """
        MATCH (cat:Category {name: $category_name})<-[:BELONGS_TO]-(d:Diagram) WITH cat, d LIMIT 15
        RETURN elementId(cat) AS source_id, labels(cat)[0] AS source_label, cat.name AS source_name,
               elementId(d) AS target_id, labels(d)[0] AS target_label, d.id AS target_name,
               'HAS_DIAGRAM' AS rel_type
        """

        # 2. Diagram -> Entity
        q2 = """
        MATCH (cat:Category {name: $category_name})<-[:BELONGS_TO]-(d:Diagram) WITH d LIMIT 15
        MATCH (d)-[:CONTAINS]->(e:Entity)
        RETURN elementId(d) AS source_id, labels(d)[0] AS source_label, d.id AS source_name,
               elementId(e) AS target_id, labels(e)[0] AS target_label, e.name AS target_name,
               'CONTAINS' AS rel_type
        """

        # 3. Entity -> Entity (Đúng cái Description mà bạn muốn)
        q3 = """
        MATCH (cat:Category {name: $category_name})<-[:BELONGS_TO]-(d:Diagram) WITH d LIMIT 15
        MATCH (d)-[:CONTAINS]->(e1:Entity)-[r]->(e2:Entity)<-[:CONTAINS]-(d)
        RETURN elementId(e1) AS source_id, labels(e1)[0] AS source_label, e1.name AS source_name,
               elementId(e2) AS target_id, labels(e2)[0] AS target_label, e2.name AS target_name,
               type(r) AS rel_type
        """

        for query in [q1, q2, q3]:
            result = session.run(query, category_name=category_name)
            for record in result:
                s_id = record["source_id"]
                t_id = record["target_id"]

                if s_id not in nodes_dict:
                    nodes_dict[s_id] = {
                        "id": s_id, "label": record["source_label"], "name": record["source_name"]
                    }
                if t_id not in nodes_dict:
                    nodes_dict[t_id] = {
                        "id": t_id, "label": record["target_label"], "name": record["target_name"]
                    }
                edges.append({
                    "source": s_id, "target": t_id, "type": record["rel_type"]
                })

    return {"nodes": list(nodes_dict.values()), "edges": edges}