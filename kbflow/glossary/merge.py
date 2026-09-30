def merge_glossary(existing, candidates):
    merged = {}
    for e in existing:
        merged[e["name"]] = dict(e)
    for c in candidates:
        name = c["name"]
        if name not in merged:
            merged[name] = dict(c)
            continue
        current = merged[name]
        if current.get("status") == "verified":
            continue
        for key, value in c.items():
            if value:
                current[key] = value
    return list(merged.values())
