from kbflow.stages.k04_knowledge import PLACEHOLDER


def _guess_name(entry):
    doc = entry.get("doc", "")
    if doc:
        return doc[:20]
    name = entry["class_name"]
    if name.endswith("Impl"):
        name = name[:-4]
    return name


def build_domain_overview(domain_name, service_name, entries):
    processes = [
        {
            "name": _guess_name(e),
            "services": service_name,
            "page_name": "-",
            "steps": PLACEHOLDER,
            "entry_api": e["class_name"],
        }
        for e in entries
    ]
    return {
        "metadata": {
            "domain": domain_name,
            "service_count": 1,
        },
        "domain_info": {
            "name": domain_name,
            "description": PLACEHOLDER,
            "scope": PLACEHOLDER,
        },
        "core_capabilities": PLACEHOLDER,
        "services": [
            {
                "id": "S01",
                "name": service_name,
                "description": PLACEHOLDER,
                "layer": "core",
                "responsibility_boundary": PLACEHOLDER,
            }
        ],
        "business_processes": processes,
        "navigation_guide": {
            "how_to_navigate": [
                "业务过程详情: 根据 business_processes.services 定位服务目录，在 01-服务概述.toon 搜索 entry_api",
                "接口详情: 在对应服务的 02-接口链路.toon 搜索 entry_api 获取完整API路径和调用链",
                "数据模型: 在对应服务的 03-数据模型.toon 查看 table_schemas 的数据表信息",
            ],
            "file_structure": [
                "%s/01-领域总览.toon (本文件)" % domain_name,
                "%s/02-跨服务链路.toon (API入口聚合)" % domain_name,
                "%s/%s/01-服务概述.toon (服务场景详情)" % (domain_name, service_name),
                "%s/%s/02-接口链路.toon (API详情+调用链)" % (domain_name, service_name),
                "%s/%s/03-数据模型.toon (表结构)" % (domain_name, service_name),
            ],
        },
    }


def build_cross_service_links(entries, topology, service_name):
    node_class = {}
    for kind in ("entries", "services", "external"):
        for n in topology.get("nodes", {}).get(kind, []):
            node_class[n["id"]] = n["class"]

    api_entries = {}
    for e in entries:
        kind = e.get("kind", "dubbo")
        api_entries.setdefault(kind, []).append({
            "class": e["class_name"],
            "methods": e.get("methods", ""),
        })

    caller_external = {}
    for edge in topology.get("edges", {}).get("external", []):
        caller = node_class.get(edge["from"], "")
        callee = node_class.get(edge["to"], "")
        if caller and callee:
            caller_external.setdefault(caller, set()).add(callee)

    external_summary = []
    if caller_external:
        all_systems = set()
        for systems in caller_external.values():
            all_systems.update(systems)
        external_summary.append({
            "service": service_name,
            "systems": "|".join(sorted(all_systems)),
        })

    return {
        "api_entries": api_entries,
        "service_dependencies_summary": [],
        "external_system_dependencies_summary": external_summary,
    }
