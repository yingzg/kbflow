import re

_DUBBO_REF_FIELD_RE = re.compile(
    r"@DubboReference(?:\s*\([^)]*\))?\s+"
    r"(?:(?:private|protected|public|static|final)\s+)*"
    r"([\w<>.?,\[\]\s]+?)\s+(\w+)\s*;"
)
_XML_REF_RE = re.compile(r"<dubbo:reference\s+([^>]+?)(?:/>|>.*?</dubbo:reference>)", re.DOTALL)
_XML_ATTR_RE = re.compile(r'(interface|id)\s*=\s*"([^"]+)"')
_POM_DEP_RE = re.compile(
    r"<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>"
    r"\s*(?:<version>([^<]+)</version>)?",
    re.DOTALL,
)
_IMPORT_RE = re.compile(r"import\s+([\w.]+)\s*;")


def _maven_coordinates(index):
    coords = {}
    for pom in index.project_dir.rglob("pom.xml"):
        text = pom.read_text(encoding="utf-8", errors="replace")
        for m in _POM_DEP_RE.finditer(text):
            gid, aid, ver = m.group(1).strip(), m.group(2).strip(), (m.group(3) or "").strip()
            coords[aid] = "%s:%s (%s)" % (gid, aid, ver) if ver else "%s:%s" % (gid, aid)
    return coords


def scan_external_dependencies(index, internal_prefixes):
    mavens = _maven_coordinates(index)
    interfaces = {}
    by_annotation = []
    by_xml = []
    for f in index.all_files():
        if "@DubboReference" not in f.content:
            continue
        for m in _DUBBO_REF_FIELD_RE.finditer(f.content):
            type_name = m.group(1).strip().split()[-1]
            field_name = m.group(2)
            pkg = _resolve_package(f.content, type_name)
            key = (pkg, type_name)
            info = interfaces.get(key)
            if info is None:
                info = {"id": "I%d" % (len(interfaces) + 1), "name": type_name, "package": pkg}
                interfaces[key] = info
            by_annotation.append({"class": f.class_name, "field": field_name, "interface_ref": info["id"]})
    for xml_path in index.project_dir.rglob("*.xml"):
        text = xml_path.read_text(encoding="utf-8", errors="replace")
        for m in _XML_REF_RE.finditer(text):
            attrs = dict(_XML_ATTR_RE.findall(m.group(1)))
            iface = attrs.get("interface", "")
            if not iface:
                continue
            pkg, name = iface.rsplit(".", 1)
            key = (pkg, name)
            info = interfaces.get(key)
            if info is None:
                info = {"id": "I%d" % (len(interfaces) + 1), "name": name, "package": pkg}
                interfaces[key] = info
            by_xml.append({"xml_file": xml_path.name, "interface_ref": info["id"]})

    interface_list = []
    for (pkg, name), info in interfaces.items():
        info["maven"] = _find_maven(mavens, name)
        interface_list.append(info)

    return {
        "internal_prefixes": internal_prefixes,
        "interfaces": interface_list,
        "by_annotation": by_annotation,
        "by_xml": by_xml,
        "mavens": mavens,
    }


def _resolve_package(content, type_name):
    for m in _IMPORT_RE.finditer(content):
        if m.group(1).endswith("." + type_name):
            return m.group(1).rsplit(".", 1)[0]
    m = re.search(r"package\s+([\w.]+)\s*;", content)
    return m.group(1) if m else ""


def _find_maven(mavens, type_name):
    for aid, coord in mavens.items():
        if type_name.lower().startswith(aid.lower()):
            return coord
    return ""
