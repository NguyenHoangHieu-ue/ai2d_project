import os
from neo4j import GraphDatabase
from pyvis.network import Network
from app.core.config import settings


def draw_user_friendly_graph():
    print("Ket noi den Neo4j de ve do thi than thien voi nguoi dung...")
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )

    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white", directed=True)

    color_map = {
        "KnowledgeBase": "#e74c3c",
        "StemDomain": "#f39c12",
        "Category": "#f1c40f",
        "Diagram": "#3498db",
        "Entity": "#2ecc71"
    }

    with driver.session() as session:
        # 1. Tầng gốc (Root -> Domain -> Category)
        q1 = """
        MATCH (n)-[r]->(m)
        WHERE labels(n)[0] IN ['KnowledgeBase', 'StemDomain', 'Category']
          AND labels(m)[0] IN ['KnowledgeBase', 'StemDomain', 'Category']
        RETURN elementId(n) AS id_n, labels(n)[0] AS label_n, n.name AS name_n,
               elementId(m) AS id_m, labels(m)[0] AS label_m, m.name AS name_m,
               type(r) AS rel_type
        """

        # 2. Category -> Diagram (Giới hạn 15 sơ đồ)
        q2 = """
        MATCH (cat:Category)<-[:BELONGS_TO]-(d:Diagram) WITH cat, d LIMIT 15
        RETURN elementId(cat) AS id_n, labels(cat)[0] AS label_n, cat.name AS name_n,
               elementId(d) AS id_m, labels(d)[0] AS label_m, d.id AS name_m,
               'HAS_DIAGRAM' AS rel_type
        """

        # 3. Diagram -> Entity
        q3 = """
        MATCH (cat:Category)<-[:BELONGS_TO]-(d:Diagram) WITH d LIMIT 15
        MATCH (d)-[:CONTAINS]->(e:Entity)
        RETURN elementId(d) AS id_n, labels(d)[0] AS label_n, d.id AS name_n,
               elementId(e) AS id_m, labels(e)[0] AS label_m, e.name AS name_m,
               'CONTAINS' AS rel_type
        """

        # 4. Entity -> Entity (Luồng câu chuyện vòng đời/thức ăn)
        q4 = """
        MATCH (cat:Category)<-[:BELONGS_TO]-(d:Diagram) WITH d LIMIT 15
        MATCH (d)-[:CONTAINS]->(e1:Entity)-[r]->(e2:Entity)<-[:CONTAINS]-(d)
        RETURN elementId(e1) AS id_n, labels(e1)[0] AS label_n, e1.name AS name_n,
               elementId(e2) AS id_m, labels(e2)[0] AS label_m, e2.name AS name_m,
               type(r) AS rel_type
        """

        queries = [q1, q2, q3, q4]

        for query in queries:
            results = session.run(query)
            for record in results:
                id_n = record["id_n"]
                label_n = record["label_n"]
                name_n = record["name_n"]

                id_m = record["id_m"]
                label_m = record["label_m"]
                name_m = record["name_m"]

                rel_type = record["rel_type"]

                # Tuỳ chỉnh hiển thị cạnh (edge) cho dễ nhìn
                edge_color = "#95a5a6"  # Màu xám mặc định
                dashes = False
                width = 1

                if rel_type == 'CONTAINS':
                    edge_color = "#7f8c8d"
                    dashes = True  # Nét đứt để làm mờ kết nối giữa Hình và Chữ
                elif rel_type in ['DEVELOPS_TO', 'EATS', 'LINKED_TO']:
                    edge_color = "#e74c3c"
                    width = 2  # In đậm luồng vòng đời/thức ăn chính màu đỏ

                net.add_node(id_n, label=str(name_n), title=label_n, color=color_map.get(label_n, "#bdc3c7"))
                net.add_node(id_m, label=str(name_m), title=label_m, color=color_map.get(label_m, "#bdc3c7"))
                net.add_edge(id_n, id_m, title=rel_type, color=edge_color, dashes=dashes, width=width)

    driver.close()

    # Bật bảng điều khiển vật lý để tắt lag khi cần
    net.show_buttons(filter_=['physics'])

    output_path = os.path.join(settings.BASE_DIR, "graph.html")
    net.write_html(output_path)
    print(f"Hoan tat! Hay mo file nay tren trinh duyet web de xem: {output_path}")


if __name__ == "__main__":
    draw_user_friendly_graph()