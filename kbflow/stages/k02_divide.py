from kbflow.toon import toon_loads


def load_entries(meta_dir):
    text = (meta_dir / "behavior.toon").read_text(encoding="utf-8")
    doc = toon_loads(text)
    entries = []
    for kind in ("dubbo", "rest", "mq", "job"):
        for bucket in ("with_doc", "no_doc"):
            for e in doc.get(kind, {}).get(bucket, []):
                entries.append({
                    "id": e["id"],
                    "class_name": e["class_name"],
                    "package": e.get("package", ""),
                    "doc": e.get("doc", ""),
                    "methods": e.get("methods", ""),
                    "kind": kind,
                    "has_doc": bucket == "with_doc",
                })
    return entries


def _as_str(value, sep=","):
    if isinstance(value, (list, tuple)):
        return sep.join(str(v) for v in value)
    return value or ""


def build_boundary_matrix(domains):
    matrix = []
    for i, d in enumerate(domains, 1):
        matrix.append({
            "id": "D%d" % i,
            "name": d["name"],
            "responsibility": d.get("responsibility", ""),
            "key_entities": _as_str(d.get("key_entities", ""), ","),
            "boundary_included": _as_str(d.get("boundary_included", ""), "|"),
            "boundary_excluded": _as_str(d.get("boundary_excluded", ""), "|"),
        })
    return matrix
