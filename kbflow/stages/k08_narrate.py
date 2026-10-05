def seal_facts(domain, service, entries, tables):
    return {
        "service": service,
        "domain": domain,
        "entry_count": len(entries),
        "entries": [e["class_name"] for e in entries],
        "table_count": len(tables),
        "tables": [t["name"] for t in tables],
    }
