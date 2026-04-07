from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, Dict, Any
from app.core.database import db
from app.models.schemas import DiagramListResponse, DiagramDetailResponse, SearchResponse
from app.services.ingestion_service import ingestion_service

router = APIRouter()

CANONICAL_CATEGORY_MAP = {
    "lifecycles": "lifeCycles",
    "lifecycle": "lifeCycles",
    "life_cycles": "lifeCycles",
    "foodchainswebs": "foodChainsWebs",
    "foodchainwebs": "foodChainsWebs",
    "food_chains_webs": "foodChainsWebs",
    "foodchains": "foodChainsWebs",
    "foodwebs": "foodChainsWebs",
}


def normalize_category(category: Optional[str]) -> Optional[str]:
    if not category:
        return None
    cleaned = category.strip()
    if not cleaned:
        return None

    if cleaned == "lifeCycles" or cleaned == "foodChainsWebs":
        return cleaned

    lowered = cleaned.lower().replace("-", "").replace(" ", "")
    if lowered in {"processes", "process", "processflow", "processflows"}:
        return None
    return CANONICAL_CATEGORY_MAP.get(lowered, cleaned)


def normalize_edges_for_category(graph: Optional[Dict[str, Any]], category: Optional[str]) -> Optional[Dict[str, Any]]:
    if not graph or not isinstance(graph, dict):
        return graph

    canonical_category = normalize_category(category)
    forced_type = None
    if canonical_category == "foodChainsWebs":
        forced_type = "EATS"
    elif canonical_category == "lifeCycles":
        forced_type = "TRANSFORME"

    if not forced_type:
        return graph

    raw_edges = graph.get("edges") or []
    normalized_edges = []
    for edge in raw_edges:
        if not isinstance(edge, dict):
            normalized_edges.append(edge)
            continue
        new_edge = dict(edge)
        new_edge["type"] = forced_type
        if "label" in new_edge:
            new_edge["label"] = forced_type
        normalized_edges.append(new_edge)

    new_graph = dict(graph)
    new_graph["edges"] = normalized_edges
    return new_graph


def normalize_relation_type(relation_type: Optional[str]) -> str:
    relation = (relation_type or "").strip().upper()
    if relation == "DEVELOPS_TO":
        return "TRANSFORME"
    return relation or "RELATED_TO"


def extract_description(doc: Dict[str, Any]) -> Optional[str]:
    top_level = doc.get("description")
    meta_level = (doc.get("meta") or {}).get("description")
    return top_level or meta_level

@router.post("/ingest/{image_id}")
async def ingest_ai_detected_data(image_id: str, ai_json: Dict[str, Any] = Body(...)):
    result = await ingestion_service.process_upload(
        raw_json_content=ai_json,
        image_id=image_id,
        rst_content=None
    )
    return result

@router.get("/diagrams", response_model=DiagramListResponse)
async def get_diagrams(category: Optional[str] = Query(None, description="Loc theo chu de")):
    normalized_category = normalize_category(category)
    query = {}
    if normalized_category:
        query["meta.category"] = normalized_category

    cursor = db.mongo_db["diagrams_inventory"].find(query)
    items = []

    async for doc in cursor:
        doc_category = doc.get("meta", {}).get("category")
        items.append({
            "id": doc.get("id"),
            "image_url": doc.get("imageUrl"),
            "meta": {
                "category": doc_category,
                "domain": doc.get("meta", {}).get("domain"),
                "description": extract_description(doc)
            },
            "graph": normalize_edges_for_category(doc.get("graph"), doc_category),
            "raw_data": None
        })

    return {"total": len(items), "items": items}


@router.get("/diagrams/{diagram_id}", response_model=DiagramDetailResponse)
async def get_diagram_detail(diagram_id: str):
    doc = await db.mongo_db["diagrams_inventory"].find_one({"id": diagram_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Khong tim thay so do")

    doc_category = doc.get("meta", {}).get("category")
    return {
        "id": doc.get("id"),
        "image_url": doc.get("imageUrl"),
        "meta": {
            "category": doc_category,
            "domain": doc.get("meta", {}).get("domain"),
            "description": extract_description(doc)
        },
        "graph": normalize_edges_for_category(doc.get("graph"), doc_category),
        "raw_data": doc.get("raw")
    }


@router.get("/search/related", response_model=SearchResponse)
async def search_related(
        keyword: str = Query(..., description="Tu khoa tim kiem"),
        category: Optional[str] = Query(None, description="Loc theo chu de")
):
    normalized_category = normalize_category(category)
    query = {
        "$or": [
            {"graph.nodes.name": {"$regex": keyword, "$options": "i"}},
            {"description": {"$regex": keyword, "$options": "i"}},
            {"meta.description": {"$regex": keyword, "$options": "i"}}
        ]
    }

    if normalized_category:
        query["meta.category"] = normalized_category

    cursor = db.mongo_db["diagrams_inventory"].find(query)
    items = []

    async for doc in cursor:
        items.append({
            "id": doc.get("id"),
            "image_url": doc.get("imageUrl"),
            "meta": {
                "category": doc.get("meta", {}).get("category"),
                "domain": doc.get("meta", {}).get("domain"),
                "description": extract_description(doc)
            }
        })

    return {"total": len(items), "items": items}


@router.get("/graph/global")
async def get_global_graph():
    if not db.neo4j_driver:
        raise HTTPException(status_code=500, detail="Neo4j khong hoat dong")

    nodes_dict = {}
    edges = []

    try:
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

            # 2. Category -> Diagram (Giới hạn 15 sơ đồ)
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

            # 4. Entity -> Entity (Vẽ Egg -> Larva -> Pupa...)
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
                        "source": s_id,
                        "target": t_id,
                        "type": normalize_relation_type(record.get("rel_type"))
                    })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {e}")

    return {"nodes": list(nodes_dict.values()), "edges": edges}


@router.get("/graph/category/{category_name}")
async def get_category_graph(category_name: str):
    if not db.neo4j_driver:
        raise HTTPException(status_code=500, detail="Neo4j khong hoat dong")

    normalized_category = normalize_category(category_name)

    nodes_dict = {}
    edges = []

    forced_edge_type = None
    if normalized_category == "foodChainsWebs":
        forced_edge_type = "EATS"
    elif normalized_category == "lifeCycles":
        forced_edge_type = "TRANSFORME"

    try:
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

            # 3. Entity -> Entity
            q3 = """
            MATCH (cat:Category {name: $category_name})<-[:BELONGS_TO]-(d:Diagram) WITH d LIMIT 15
            MATCH (d)-[:CONTAINS]->(e1:Entity)-[r]->(e2:Entity)<-[:CONTAINS]-(d)
            RETURN elementId(e1) AS source_id, labels(e1)[0] AS source_label, e1.name AS source_name,
                   elementId(e2) AS target_id, labels(e2)[0] AS target_label, e2.name AS target_name,
                   type(r) AS rel_type
            """

            for query in [q1, q2, q3]:
                result = session.run(query, category_name=normalized_category or category_name)
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
                    rel_type = forced_edge_type or normalize_relation_type(record.get("rel_type"))
                    edges.append({
                        "source": s_id, "target": t_id, "type": rel_type
                    })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Category graph query failed: {e}")

    return {"nodes": list(nodes_dict.values()), "edges": edges}