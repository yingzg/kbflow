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
        queue = [entry_node]
        tables_found = set()
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            cls = node_class.get(node, "")
            if cls in mapper_tables:
                tables_found.update(mapper_tables[cls])
            elif cls.endswith("Mapper"):
                tables_found.add(_mapper_to_table(cls))
            for nxt in adj.get(node, []):
                if nxt not in visited:
                    queue.append(nxt)
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


def generate_data_model_skeleton(tables, entry_tables, entries):
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
        "table_class_map": [
            {"table": t, "entry_classes": "|".join(cs)}
            for t, cs in table_classes.items()
        ],
        "table_schemas": [{"table": t["name"], "ddl": t["ddl"]} for t in tables],
    }


def _parse_methods(methods_str):
    result = []
    for part in methods_str.split(";"):
        part = part.strip()
        if not part:
            continue
        if "(" in part and part.endswith(")"):
            name, _, doc = part.partition("(")
            result.append({"name": name.strip(), "doc": doc.rstrip(")")})
        else:
            result.append({"name": part, "doc": ""})
    return result


def _method_names(methods_str, limit=15):
    names = []
    for part in methods_str.split(";"):
        part = part.strip()
        if not part:
            continue
        name = part.split("(")[0].strip()
        if name and name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return "|".join(names)


_ENRICH_SYSTEM = (
    "你是领域知识文档写作者。你根据服务的业务入口（类名+方法名），"
    "补充服务定位、核心职责和场景描述。只输出 JSON，不要多余文字。"
)


def enrich_overview(llm, domain, service, overview, entries):
    import json

    entry_desc = "\n".join(
        "%s: %s" % (e["class_name"], _method_names(e.get("methods", "")))
        for e in entries
    )
    scenario_desc = "\n".join(
        "%s: %s" % (s["id"], s["entry_class"])
        for bucket in ("P0", "P1", "P2")
        for s in overview["scenarios"].get(bucket, [])
    )
    prompt = (
        "服务「%s」在领域「%s」有 %d 个业务入口：\n%s\n\n"
        "场景清单（场景ID：入口类）：\n%s\n\n"
        "请补充服务概述，返回 JSON：\n"
        '{"description": 一句话服务定位, "core_responsibilities": [3-5条核心职责], '
        '"scenarios": {"场景ID": {"name": 语义名, "desc": 一句话描述}}}\n\n'
        "只输出 JSON。"
        % (service, domain, len(entries), entry_desc, scenario_desc)
    )
    resp = llm.complete(prompt, system=_ENRICH_SYSTEM)
    m = re.search(r"\{.*\}", resp, re.DOTALL)
    if not m:
        return overview
    data = json.loads(m.group(0))

    if data.get("description"):
        overview["service_info"]["description"] = data["description"]
    if data.get("core_responsibilities"):
        overview["service_info"]["core_responsibilities"] = data["core_responsibilities"]
    scenarios = data.get("scenarios", {})
    for bucket in ("P0", "P1", "P2"):
        for s in overview["scenarios"].get(bucket, []):
            info = scenarios.get(s["id"], {})
            if info.get("name"):
                s["name"] = info["name"]
            if info.get("desc"):
                s["desc"] = info["desc"]
    return overview
