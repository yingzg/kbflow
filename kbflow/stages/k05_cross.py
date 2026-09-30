import json
import re

from kbflow.stages.k04_knowledge import PLACEHOLDER

_ENRICH_SYSTEM = (
    "你是领域驱动设计专家。你根据领域的业务入口，补充领域定位和边界。只输出 JSON，不要多余文字。"
)


def enrich_domain_overview(llm, domain_name, overview, entries):
    entry_desc = "\n".join(e["class_name"] for e in entries)
    prompt = (
        "领域「%s」有 %d 个业务入口：\n%s\n\n"
        "请补充领域总览，返回 JSON：\n"
        '{"description": 一句话领域定位, "scope": 领域边界描述（一句话，包含什么能力、不含什么）}\n\n'
        "只输出 JSON。"
        % (domain_name, len(entries), entry_desc)
    )
    resp = llm.complete(prompt, system=_ENRICH_SYSTEM)
    m = re.search(r"\{.*\}", resp, re.DOTALL)
    if not m:
        return overview
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return overview
    if data.get("description"):
        overview["description"] = data["description"]
    if data.get("scope"):
        overview["scope"] = data["scope"]
    return overview


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
        "domain": domain_name,
        "description": PLACEHOLDER,
        "scope": PLACEHOLDER,
        "services": [
            {
                "id": "S01",
                "name": service_name,
                "description": PLACEHOLDER,
                "responsibility_boundary": PLACEHOLDER,
            }
        ],
        "business_processes": processes,
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
