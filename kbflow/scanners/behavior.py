import re

from kbflow.scanners.file_index import JavaFile
from kbflow.scanners.javadoc import extract_class_doc, extract_method_doc
from kbflow.scanners.method_filter import filter_methods

_DUBBO_RE = re.compile(r"@DubboService")
_REST_RE = re.compile(r"@RestController")
_MQ_RE = re.compile(r"@(?:RocketMQMessageListener|KafkaListener|RabbitListener)")
_JOB_RE = re.compile(r"@(?:Scheduled|XxlJob|ElasticJob)")

_IMPLEMENTS_RE = re.compile(r"implements\s+([\w,\s<>]+?)(?:\s*\{|$)")
_METHOD_RE = re.compile(
    r"(?:(?:public|private|protected|static|final|synchronized|abstract|native|default)\s+)*"
    r"([\w<>.?,\[\]\s]+?)\s+"
    r"(\w+)\s*"
    r"\(([^()]*)\)"
    r"(?:\s*throws\s+[\w\s,]+)?"
    r"\s*(?:\{|;)",
    re.DOTALL,
)
_FIELD_RE = re.compile(r"private\s+(?:static\s+|final\s+)*[\w<>.?,\[\]\s]+?\s+(\w+)\s*[;=]")
_CLASS_DECL_RE = re.compile(r"\b(?:public\s+)?(?:abstract\s+|final\s+)?(?:class|interface|enum)\s+\w+")
_MAPPING_RE = re.compile(r"@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*\(([^)]*)\)")


def _class_decl_start(content):
    m = _CLASS_DECL_RE.search(content)
    return m.start() if m else 0
_HTTP_METHODS = {
    "GetMapping": "GET", "PostMapping": "POST", "PutMapping": "PUT",
    "DeleteMapping": "DELETE", "PatchMapping": "PATCH", "RequestMapping": "GET",
}


def _extract_methods(content):
    methods = []
    for m in _METHOD_RE.finditer(content):
        ret_type = m.group(1).strip()
        name = m.group(2)
        if ret_type.endswith(("new", "throw", "return")):
            continue
        params_str = m.group(3)
        params = [p.strip() for p in params_str.split(",") if p.strip()]
        doc = extract_method_doc(content, m.start())
        methods.append({"name": name, "params": params, "doc": doc})
    return methods


def _extract_field_names(content):
    return {m.group(1) for m in _FIELD_RE.finditer(content)}


def _filtered_methods(content):
    methods = _extract_methods(content)
    fields = _extract_field_names(content)
    kept, truncated = filter_methods(methods, fields)
    return kept, truncated


def _interface_doc(index, interface_name):
    iface = index.find_by_class_name(interface_name)
    if iface is None:
        return "", {}
    doc = extract_class_doc(iface.content, _class_decl_start(iface.content))
    method_docs = {}
    for m in _extract_methods(iface.content):
        if m["doc"]:
            method_docs[m["name"]] = m["doc"]
    return doc, method_docs


def _dubbo_entries(index):
    entries = []
    for f in index.all_files():
        if not _DUBBO_RE.search(f.content):
            continue
        m = _IMPLEMENTS_RE.search(f.content)
        interface_name = m.group(1).strip().split(",")[0].strip() if m else ""
        class_doc = extract_class_doc(f.content, _class_decl_start(f.content))
        iface_doc, iface_method_docs = _interface_doc(index, interface_name) if interface_name else ("", {})
        doc = iface_doc or class_doc
        kept, truncated = _filtered_methods(f.content)
        methods = []
        for meth in kept:
            mdoc = iface_method_docs.get(meth["name"], "") or meth["doc"]
            methods.append({"name": meth["name"], "doc": mdoc})
        entries.append({
            "class_name": f.class_name,
            "package": f.package,
            "interface_name": interface_name,
            "doc": doc,
            "methods": methods,
            "truncated": len(truncated),
            "discovery": "annotation",
        })
    return entries


def _rest_entries(index):
    entries = []
    for f in index.all_files():
        if not _REST_RE.search(f.content):
            continue
        base_path = ""
        m = re.search(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']?([^"\')\s]*)', f.content)
        if m:
            base_path = m.group(1)
        class_doc = extract_class_doc(f.content, _class_decl_start(f.content))
        kept, truncated = _filtered_methods(f.content)
        methods = []
        for meth in kept:
            methods.append({
                "name": meth["name"],
                "doc": meth["doc"],
                "http_method": "GET",
                "path": "",
            })
        entries.append({
            "class_name": f.class_name,
            "package": f.package,
            "interface_name": "",
            "doc": class_doc,
            "base_path": base_path,
            "methods": methods,
            "truncated": len(truncated),
            "discovery": "annotation",
        })
    return entries


def _mq_entries(index):
    entries = []
    for f in index.all_files():
        if not _MQ_RE.search(f.content):
            continue
        topic = ""
        m = re.search(r'topic\s*=\s*"([^"]+)"', f.content)
        if m:
            topic = m.group(1)
        class_doc = extract_class_doc(f.content, _class_decl_start(f.content))
        kept, _ = _filtered_methods(f.content)
        entries.append({
            "class_name": f.class_name,
            "package": f.package,
            "interface_name": "",
            "doc": class_doc,
            "topic": topic,
            "methods": [{"name": x["name"], "doc": x["doc"]} for x in kept],
            "discovery": "annotation",
        })
    return entries


def _job_entries(index):
    entries = []
    for f in index.all_files():
        if not _JOB_RE.search(f.content):
            continue
        class_doc = extract_class_doc(f.content, _class_decl_start(f.content))
        kept, _ = _filtered_methods(f.content)
        jobs = []
        for m in re.finditer(r"@(Scheduled|XxlJob)\s*\(([^)]*)\)", f.content):
            cron = ""
            cm = re.search(r'cron\s*=\s*"([^"]+)"', m.group(2))
            if cm:
                cron = cm.group(1)
            jobs.append({"annotation": m.group(1), "cron": cron})
        entries.append({
            "class_name": f.class_name,
            "package": f.package,
            "interface_name": "",
            "doc": class_doc,
            "jobs": jobs,
            "methods": [{"name": x["name"], "doc": x["doc"]} for x in kept],
            "discovery": "annotation",
        })
    return entries


def scan_behavior(index):
    return {
        "dubbo": _dubbo_entries(index),
        "rest": _rest_entries(index),
        "mq": _mq_entries(index),
        "job": _job_entries(index),
    }
