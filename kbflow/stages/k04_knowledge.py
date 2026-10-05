import re

PLACEHOLDER = "[待AI补充]"


def _humanize(name):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return s.lower()


def _guess_name(entry):
    if entry.get("doc"):
        return entry["doc"][:20]
    return _humanize(entry["class_name"])


def _priority(kind):
    return {"dubbo": "P0", "rest": "P1", "mq": "P2", "job": "P2"}.get(kind, "P2")


def generate_overview_skeleton(domain_name, service_name, entries):
    by_priority = {"P0": [], "P1": [], "P2": []}
    for i, e in enumerate(entries, 1):
        by_priority[_priority(e.get("kind", ""))].append({
            "id": "SC-%03d" % i,
            "entry_class": e["class_name"],
            "name": _guess_name(e),
            "trigger": e.get("kind", ""),
            "desc": PLACEHOLDER,
        })
    return {
        "service_info": {
            "name": service_name,
            "domain": domain_name,
            "description": PLACEHOLDER,
            "core_responsibilities": PLACEHOLDER,
        },
        "service_boundaries": {
            "owns": PLACEHOLDER,
            "delegates_to": PLACEHOLDER,
            "provides_to": PLACEHOLDER,
        },
        "dependencies": {
            "upstream": PLACEHOLDER,
            "downstream": PLACEHOLDER,
            "mq_upstream": PLACEHOLDER,
            "mq_downstream": PLACEHOLDER,
        },
        "scenarios": by_priority,
    }


def _mapper_to_table(mapper_class):
    name = mapper_class[:-6] if mapper_class.endswith("Mapper") else mapper_class
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def _node_class_map(topology):
    node_class = {}
    for kind in ("entries", "services", "external"):
        for n in topology.get("nodes", {}).get(kind, []):
            node_class[n["id"]] = n["class"]
    return node_class


def _find_node(topology, class_name):
    for kind in ("entries", "services", "external"):
        for n in topology.get("nodes", {}).get(kind, []):
            if n["class"] == class_name:
                return n["id"]
    return None


def _map_entry_tables(entries, topology, tables, mapper_tables):
    node_class = _node_class_map(topology)
    adj = {}
    for edge in topology.get("edges", {}).get("internal", []):
        adj.setdefault(edge["from"], []).append(edge["to"])
    result = {}
    for e in entries:
        entry_node = _find_node(topology, e["class_name"])
        if not entry_node:
            continue
        visited = set()
        queue = [(entry_node, 0)]
        tables_found = set()
        while queue:
            node, depth = queue.pop(0)
            if node in visited or depth > 2:
                continue
            visited.add(node)
            cls = node_class.get(node, "")
            if cls in mapper_tables:
                tables_found.update(mapper_tables[cls])
            elif cls.endswith("Mapper"):
                tables_found.add(_mapper_to_table(cls))
            for nxt in adj.get(node, []):
                if nxt not in visited:
                    queue.append((nxt, depth + 1))
        if tables_found:
            result[e["id"]] = sorted(tables_found)
    return [{"entry_id": eid, "tables": "|".join(ts)} for eid, ts in result.items()]


def _map_external_dependencies(topology, entries):
    entry_classes = {e["class_name"] for e in entries}
    node_class = _node_class_map(topology)
    result = []
    for edge in topology.get("edges", {}).get("external", []):
        caller = node_class.get(edge["from"], "")
        callee = node_class.get(edge["to"], "")
        if caller in entry_classes and callee:
            result.append({"caller_class": caller, "interface": callee})
    return result


def generate_interface_skeleton(entries, topology, tables, mapper_tables=None):
    mapper_tables = mapper_tables or {}
    api_entries = [
        {
            "id": e["id"],
            "type": e.get("kind", ""),
            "class": e["class_name"],
            "methods": e.get("methods", ""),
        }
        for e in entries
    ]
    return {
        "api_entries": api_entries,
        "entry_tables": _map_entry_tables(entries, topology, tables, mapper_tables),
        "external_dependencies": _map_external_dependencies(topology, entries),
    }


def generate_data_model_skeleton(service_name, domain_name, tables, entry_tables, entries):
    entry_id_to_class = {e["id"]: e["class_name"] for e in entries}
    table_classes = {}
    for et in entry_tables:
        class_name = entry_id_to_class.get(et["entry_id"], "")
        for t in et["tables"].split("|"):
            if t:
                table_classes.setdefault(t, [])
                if class_name and class_name not in table_classes[t]:
                    table_classes[t].append(class_name)
    return {
        "metadata": {
            "service": service_name,
            "domain": domain_name,
            "table_count": len(tables),
        },
        "table_class_map": [
            {"name": t, "comment": PLACEHOLDER, "classes": "|".join(cs)}
            for t, cs in table_classes.items()
        ],
        "table_schemas": [{"table": t["name"], "ddl": t["ddl"]} for t in tables],
    }
