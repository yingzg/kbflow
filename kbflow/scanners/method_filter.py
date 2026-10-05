import re

_JAVA_KEYWORDS = frozenset({
    "if", "for", "while", "switch", "case", "default", "catch", "try", "finally",
    "throw", "return", "new", "else", "do", "break", "continue", "synchronized",
    "class", "interface", "enum", "assert", "super", "this", "instanceof",
    "static", "import", "package", "public", "private", "protected",
})

HARD_SKIP_NAMES = frozenset({
    "toString", "hashCode", "equals", "clone", "getClass", "finalize",
    "wait", "notify", "notifyAll",
    "init", "destroy", "afterPropertiesSet", "onApplicationEvent", "close", "shutdown",
}).union(_JAVA_KEYWORDS)

ACTION_VERBS = frozenset({
    "create", "insert", "add", "update", "modify", "delete", "remove", "approve",
    "audit", "reject", "confirm", "cancel", "submit", "apply", "review", "settle",
    "transfer", "deduct", "refund", "export", "import", "generate", "calculate",
    "sync", "notify", "send", "execute", "process",
})

QUERY_VERBS = frozenset({"query", "find", "list", "search", "load"})

_ACCESSOR = ("get", "set", "is")
_CHECKERS = ("check", "validate", "isValid")
_CAMEL_HEAD_RE = re.compile(r"[a-z]+")


def _camel_head(name):
    m = _CAMEL_HEAD_RE.match(name)
    return m.group(0).lower() if m else ""


def classify_method(name, params, field_names, has_doc):
    if name in HARD_SKIP_NAMES:
        return "hard_skip"

    head = _camel_head(name)

    if head in _ACCESSOR and len(name) > len(head):
        rest = name[len(head):]
        field_lower = rest[0].lower() + rest[1:]
        if field_lower in field_names:
            return "deprioritize"
        return "normal"

    if head in _CHECKERS:
        if not params:
            return "deprioritize"
        return "normal"

    if head in ACTION_VERBS or head in QUERY_VERBS:
        return "priority"

    if has_doc:
        return "priority"

    return "normal"


def filter_methods(methods, field_names, max_keep=20):
    _ORDER = {"priority": 0, "normal": 1, "deprioritize": 2}
    tagged = []
    for m in methods:
        name = m["name"]
        params = m.get("params", [])
        doc = m.get("doc", "")
        cls = classify_method(name, params, field_names, bool(doc))
        if cls == "hard_skip":
            continue
        item = dict(m)
        item["_cls"] = cls
        tagged.append(item)

    tagged.sort(key=lambda x: _ORDER[x["_cls"]])

    kept = tagged[:max_keep]
    truncated = tagged[max_keep:]
    for item in kept + truncated:
        item.pop("_cls", None)
    return kept, truncated
