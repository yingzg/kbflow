import re

_DUBBO_REF_RE = re.compile(
    r"@DubboReference(?:\s*\([^)]*\))?\s+"
    r"(?:(?:private|protected|public|static|final)\s+)*"
    r"([\w<>.?,\[\]\s]+?)\s+(\w+)\s*;"
)
_AUTOWIRED_RE = re.compile(
    r"@(?:Autowired|Resource|Inject)(?:\([^)]*\))?\s+"
    r"(?:(?:private|protected|public|static|final)\s+)*"
    r"([\w<>.?,\[\]\s]+?)\s+(\w+)\s*;"
)
_FINAL_FIELD_RE = re.compile(
    r"private\s+final\s+([\w<>.?,\[\]\s]+?)\s+(\w+)\s*;"
)
_IMPL_SUFFIXES = ("Impl", "ServiceImpl", "Manager", "Service", "Mapper")


def scan_topology(index, behavior, internal_prefixes):
    nodes = {"entries": [], "services": [], "external": []}
    edges = {"internal": [], "external": []}
    unresolved = []
    node_ids = {}
    visited = set()
    entry_map = {}

    entry_counter = [1]
    for kind in ("dubbo", "rest", "mq", "job"):
        for e in behavior.get(kind, []):
            nid = "N%04d" % entry_counter[0]
            entry_counter[0] += 1
            node_ids[e["class_name"]] = nid
            entry_map[e["class_name"]] = e
            nodes["entries"].append({
                "id": nid,
                "class": e["class_name"],
                "type": kind,
            })

    svc_counter = [1]
    ext_counter = [1]

    def trace(class_name, parent_nid):
        if class_name in visited:
            return
        visited.add(class_name)
        f = index.find_by_class_name(class_name)
        if f is None:
            return
        for type_name, field_name, is_external_ref in _injections(f.content):
            simple = type_name.split(".")[-1]
            if is_external_ref or _is_external(index, f.content, simple, internal_prefixes):
                eid = node_ids.get(simple)
                if eid is None:
                    eid = "E%04d" % ext_counter[0]
                    ext_counter[0] += 1
                    node_ids[simple] = eid
                    nodes["external"].append({"id": eid, "class": simple})
                edges["external"].append({"from": parent_nid, "to": eid, "kind": "dubbo_reference"})
                continue
            impl = _find_impl(index, simple)
            if impl is None:
                unresolved.append({"interface": simple, "from": class_name})
                continue
            sid = node_ids.get(impl)
            if sid is None:
                sid = "S%04d" % svc_counter[0]
                svc_counter[0] += 1
                node_ids[impl] = sid
                nodes["services"].append({"id": sid, "class": impl, "pkg": index.find_by_class_name(impl).package})
            edges["internal"].append({"from": parent_nid, "to": sid, "kind": "injection"})
            trace(impl, sid)

    for class_name, nid in list(node_ids.items()):
        if class_name in entry_map:
            trace(class_name, nid)

    return {
        "nodes": nodes,
        "edges": edges,
        "unresolved": unresolved,
    }


def _injections(content):
    results = []
    for m in _DUBBO_REF_RE.finditer(content):
        results.append((m.group(1).strip().split()[-1], m.group(2), True))
    for m in _AUTOWIRED_RE.finditer(content):
        results.append((m.group(1).strip().split()[-1], m.group(2), False))
    if "@RequiredArgsConstructor" in content:
        for m in _FINAL_FIELD_RE.finditer(content):
            results.append((m.group(1).strip().split()[-1], m.group(2), False))
    return results


def _is_external(index, content, type_name, internal_prefixes):
    m = re.search(r"import\s+([\w.]+\.%s)\s*;" % re.escape(type_name), content)
    if m:
        fqn = m.group(1)
        return not any(fqn.startswith(p) for p in internal_prefixes)
    return False


def _find_impl(index, type_name):
    f = index.find_by_class_name(type_name)
    if f is None:
        return None
    if _is_interface(f.content):
        impl = _find_implementer(index, type_name)
        if impl:
            return impl
        for suffix in _IMPL_SUFFIXES:
            candidate = type_name + suffix
            if index.find_by_class_name(candidate) is not None:
                return candidate
        return type_name
    return type_name


def _is_interface(content):
    return re.search(r"(?<!@)\b(?:public\s+)?(?:abstract\s+)?interface\s+\w+", content) is not None


def _find_implementer(index, interface_name):
    for f in index.all_files():
        if re.search(r"\bclass\s+\w+\s+implements\s+[\w,\s<>]*\b%s\b" % re.escape(interface_name), f.content):
            return f.class_name
    return None
