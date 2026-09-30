def categorize(entries):
    for e in entries:
        has_class_doc = bool(e.get("doc"))
        methods = e.get("methods", [])
        with_doc = [m for m in methods if m.get("doc")]
        no_doc = [m for m in methods if not m.get("doc")]
        if has_class_doc:
            if with_doc and not no_doc:
                e["cat"] = "cat1"
            elif with_doc and no_doc:
                e["cat"] = "cat2"
            else:
                e["cat"] = "cat3"
        else:
            if with_doc:
                e["cat"] = "cat4"
            else:
                e["cat"] = "cat5"
    return entries


def group_by_cat(entries):
    categorized = categorize(entries)
    groups = {"cat1": [], "cat2": [], "cat3": [], "cat4": [], "cat5": []}
    for e in categorized:
        groups[e["cat"]].append(e)
    return groups
