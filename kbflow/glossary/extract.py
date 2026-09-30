import re

_SUFFIXES = (
    "ServiceImpl", "Service", "Controller", "Manager", "Mapper", "Job", "Consumer",
    "Listener", "Facade", "Repository", "Impl", "Config", "Handler", "Converter",
)


def strip_suffix(class_name):
    for suffix in _SUFFIXES:
        if class_name.endswith(suffix) and len(class_name) > len(suffix):
            return class_name[: -len(suffix)]
    return class_name


def infer_scope(package):
    parts = [p for p in package.split(".") if p]
    return parts[-1] if parts else package


def extract_candidates(entries, key_entities=None):
    candidates = []
    seen = set()
    if key_entities:
        for ke in key_entities.split(","):
            ke = ke.strip()
            if ke and ke not in seen:
                seen.add(ke)
                candidates.append({
                    "name": ke,
                    "zh": "",
                    "scope": "",
                    "code": "",
                    "aliases": "",
                    "avoid": "",
                    "confusable": "",
                    "status": "draft",
                    "provenance": "",
                })
    for e in entries:
        base = strip_suffix(e["class_name"])
        if not base or base in seen:
            continue
        seen.add(base)
        candidates.append({
            "name": base,
            "zh": "",
            "scope": infer_scope(e.get("package", "")),
            "code": e["class_name"],
            "aliases": "",
            "avoid": "",
            "confusable": "",
            "status": "draft",
            "provenance": "",
        })
    return candidates
