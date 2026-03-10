import logging

logger = logging.getLogger(__name__)

CONTEXT_RULES = {
    "foodChainsWebs": {"relation": "EATS", "default_label": "Organism"},
    "lifeCycles": {"relation": "DEVELOPS_TO", "default_label": "Stage"}
}


def get_context(image_id, categories, mapping_df):
    cat = categories.get(image_id)
    if cat not in CONTEXT_RULES:
        return None
    try:
        if not mapping_df.empty:
            row = mapping_df[mapping_df['category'] == cat]
            if not row.empty:
                return {
                    "category": cat,
                    "domain": row.iloc[0]['stem_domain'],
                    "label": row.iloc[0]['node_label'],
                    "desc_template": row.iloc[0]['description']
                }
    except:
        pass
    return {"category": cat, "domain": "Biology", "label": "Entity"}


def process_logic(std_data, rst_data, context):
    image_id = std_data['id']
    category = context['category']
    default_label = context['label']

    nodes = []
    edges = []

    blob_names_map = {}

    texts = std_data['visual_objects'].get('texts', [])
    blobs = std_data['visual_objects'].get('blobs', {})

    def find_text_content(tid):
        for t in texts:
            if t['id'] == tid: return t['content']
        return tid

    # TIM TEN GOC TU RST
    if rst_data:
        rst_lookup = {item['id']: item for item in rst_data.get('rst', []) + rst_data.get('grouping', [])}

        def resolve_copy_of(node_id):
            curr = node_id
            visited = set()
            while curr not in visited:
                visited.add(curr)
                node = rst_lookup.get(curr)
                if not node: return curr

                data = node.get('data', {})
                if 'copy_of' in data:
                    curr = data['copy_of']
                else:
                    return curr
            return curr

        parent_map = {}
        label_map = {}

        all_items = rst_data.get('rst', []) + rst_data.get('grouping', [])

        for item in all_items:
            nid = item['id']
            d = item.get('data', {})
            kind = d.get('kind')

            if kind == 'group':
                for adj in item.get('adjacencies', []):
                    child = adj.get('nodeTo')
                    if child:
                        real_child = resolve_copy_of(child)
                        parent_map[real_child] = nid

            if d.get('rel_name') in ['identification', 'class-ascription']:
                target = d.get('nucleus')
                txt = d.get('satellites')
                if target and txt:
                    real_target = resolve_copy_of(target)
                    real_text_id = resolve_copy_of(txt.split()[0])

                    if real_target not in label_map:
                        label_map[real_target] = real_text_id

        for b_id in blobs.keys():
            curr_id = b_id
            found_name = None

            for _ in range(10):
                if curr_id in label_map:
                    text_id = label_map[curr_id]
                    found_name = find_text_content(text_id)
                    break

                if curr_id in parent_map:
                    curr_id = parent_map[curr_id]
                else:
                    break

            if found_name:
                blob_names_map[b_id] = found_name

    # XU LY TRUNG TEN
    name_counts = {}
    for name in blob_names_map.values():
        name_counts[name] = name_counts.get(name, 0) + 1

    name_indices = {}

    for b_id in sorted(blob_names_map.keys()):
        raw_name = blob_names_map[b_id]
        if name_counts[raw_name] > 1:
            if raw_name not in name_indices:
                name_indices[raw_name] = 1

            new_name = f"{raw_name} {name_indices[raw_name]}"
            blob_names_map[b_id] = new_name
            name_indices[raw_name] += 1

    # TAO NODES
    final_blob_names = {}

    for b_id, b_info in blobs.items():
        node_name = blob_names_map.get(b_id, b_id)
        final_blob_names[b_id] = node_name
        nodes.append({
            "uid": f"{image_id}_{b_id}",
            "id": b_id,
            "name": node_name,
            "type": default_label,
            "bbox": b_info.get('bbox')
        })

    used_texts = set(blob_names_map.values())
    for t in texts:
        if t['content'] not in used_texts:
            nodes.append({
                "uid": f"{image_id}_{t['id']}",
                "id": t['id'],
                "name": t['content'],
                "type": "Label",
                "bbox": t.get('bbox')
            })
            final_blob_names[t['id']] = t['content']

    # TAO EDGES
    relation_type = CONTEXT_RULES.get(category, {}).get("relation", "LINKED_TO")

    for rel in std_data.get('relationships', []):
        if rel.get('type') == 'connection':
            src = rel.get('from')
            tgt = rel.get('to')
            if src in final_blob_names and tgt in final_blob_names:
                edges.append({
                    "source": f"{image_id}_{src}",
                    "target": f"{image_id}_{tgt}",
                    "relation": relation_type,
                    "via": rel.get('via')
                })

    if not edges and rst_data:
        all_items = rst_data.get('rst', [])

        def get_blobs_from_rst_node(node_id):
            results = []
            stack = [node_id]
            visited = set()
            lookup = {i['id']: i for i in all_items + rst_data.get('grouping', [])}

            while stack:
                curr_raw = stack.pop()
                if curr_raw in visited: continue
                visited.add(curr_raw)

                curr = resolve_copy_of(curr_raw)
                if curr.startswith('B') or curr.startswith('T'):
                    results.append(curr)
                    continue

                node = lookup.get(curr)
                if not node: continue

                d = node.get('data', {})
                kind = d.get('kind')

                if kind == 'group':
                    for adj in node.get('adjacencies', []):
                        if adj.get('nodeTo'): stack.append(adj.get('nodeTo'))
                elif kind == 'relation':
                    if d.get('nucleus'): stack.append(d.get('nucleus'))
                    if d.get('nuclei'): stack.extend(d.get('nuclei').split())
            return list(set(results))

        for item in all_items:
            d = item.get('data', {})
            rel = d.get('rel_name')

            if rel in ['sequence', 'cyclic sequence']:
                raw_steps = d.get('nuclei', '').split()
                step_blobs = [get_blobs_from_rst_node(s) for s in raw_steps if s]

                for i in range(len(step_blobs) - 1):
                    for s in step_blobs[i]:
                        for t in step_blobs[i + 1]:
                            if s != t and s in final_blob_names and t in final_blob_names:
                                edges.append({"source": f"{image_id}_{s}", "target": f"{image_id}_{t}",
                                              "relation": relation_type})

                if rel == 'cyclic sequence' and len(step_blobs) > 1:
                    for s in step_blobs[-1]:
                        for t in step_blobs[0]:
                            if s != t and s in final_blob_names and t in final_blob_names:
                                edges.append({"source": f"{image_id}_{s}", "target": f"{image_id}_{t}",
                                              "relation": relation_type})

    # Xoa trung lap
    unique_edges = []
    seen_edges = set()
    for edge in edges:
        sig = (edge['source'], edge['target'], edge['relation'])
        if sig not in seen_edges:
            seen_edges.add(sig)
            unique_edges.append(edge)

    # SAP XEP CANH
    if category == 'lifeCycles' and unique_edges:
        # Tao danh sach ke va tinh in-degree
        adj_list = {}
        in_degree = {}
        out_degree = {}
        edge_map = {}  # Map (source, target) -> edge object

        for edge in unique_edges:
            s = edge['source']
            t = edge['target']

            if s not in adj_list: adj_list[s] = []
            adj_list[s].append(t)

            out_degree[s] = out_degree.get(s, 0) + 1
            in_degree[t] = in_degree.get(t, 0) + 1
            if s not in in_degree: in_degree[s] = 0
            if t not in out_degree: out_degree[t] = 0

            edge_map[(s, t)] = edge

        # Tim Start Node
        start_node = None

        # Uu tien 1: Node co in-degree = 0 (khong ai tro vao no)
        for node, degree in in_degree.items():
            if degree == 0:
                start_node = node
                break

        # Uu tien 2: Neu la vong tron (ai cung in=1, out=1), tim chu "Egg", "Seed"
        if not start_node:
            for node_uid in adj_list.keys():
                node_name = next((n['name'] for n in nodes if n['uid'] == node_uid), "").lower()
                if "egg" in node_name or "seed" in node_name or "stage a" in node_name:
                    start_node = node_uid
                    break

        # Uu tien 3: Chon bua node dau tien trong danh sach
        if not start_node:
            start_node = list(adj_list.keys())[0]

        # Duyet duong di (Path traversing)
        sorted_edges = []
        visited_edges = set()
        curr_node = start_node

        # Gioi han vong lap de tranh treo
        max_iters = len(unique_edges) * 2

        while curr_node in adj_list and max_iters > 0:
            max_iters -= 1
            next_node = None

            # Tim 1 node tiep theo chua duoc di qua
            for neighbor in adj_list[curr_node]:
                if (curr_node, neighbor) not in visited_edges:
                    next_node = neighbor
                    break

            if next_node:
                visited_edges.add((curr_node, next_node))
                sorted_edges.append(edge_map[(curr_node, next_node)])
                curr_node = next_node
            else:
                break  # Het duong

        # Neu co canh nao bi sot (vi do thi tach roi), them vao cuoi
        for edge in unique_edges:
            if (edge['source'], edge['target']) not in visited_edges:
                sorted_edges.append(edge)

        unique_edges = sorted_edges

    return nodes, unique_edges