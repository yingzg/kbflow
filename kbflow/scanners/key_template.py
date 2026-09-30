import re

from kbflow.scanners.javadoc import extract_method_doc

KIND_ANNOTATIONS = {
    "lock": ["DistributedLock", "Lock", "RedisLock", "RedissonLock", "CacheLock"],
    "idempotent": ["Idempotent"],
    "cache": ["Cacheable", "CacheEvict", "CachePut"],
}

_ANNOTATION_NAME_TO_KIND = {}
for _kind, _names in KIND_ANNOTATIONS.items():
    for _name in _names:
        _ANNOTATION_NAME_TO_KIND[_name] = _kind

_IDENT_RE = re.compile(r"[A-Za-z_]\w*")
_UPPER_CONST_RE = re.compile(r"[A-Z][A-Z0-9_]*")
_VAR_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_]\w*)\}")
_SPEL_VAR_RE = re.compile(r"#([A-Za-z_]\w*)")

_ANNOTATION_RE = re.compile(r"@(\w+)\s*(?:\(([^)]*)\))?")
_ATTR_RE = re.compile(r"(\w+)\s*=\s*(\"[^\"]*\"|'[^']*'|#[^\s,)]+|\{[^}]*\}|[^,\s)]+)")
_LOCK_CALL_RE = re.compile(r"\b(tryLock|lock|getLock|setIfAbsent|acquire)\s*\(([^()]*)\)")
_CACHE_CALL_RE = re.compile(
    r"\b(redisTemplate|\w*[Rr]edis\w*|\w*[Cc]ache\w*)\b"
    r"(?:\.[a-zA-Z_]\w*\([^()]*\))*"
    r"\.(get|set|delete|put|getForObject|setIfAbsent)\s*\(([^()]*)\)"
)
_SHARD_RE = re.compile(r"\b(\w+)(?:\.\w+\([^)]*\))?\s*%\s*(\d+)")

_METHOD_SIG_RE = re.compile(
    r"(?:(?:public|private|protected|static|final|synchronized|abstract|native|default)\s+)*"
    r"(?:[\w<>.?,\[\]\s]+?)\s+"
    r"(?P<name>\w+)\s*"
    r"\([^()]*\)"
    r"(?:\s*throws\s+[\w\s,]+)?"
    r"\s*\{",
    re.DOTALL,
)
_KEYWORD_FILTER = {"if", "for", "while", "switch", "return", "new", "catch", "synchronized", "throw"}


def normalize_key_pattern(raw):
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("#"):
        return _normalize_spel(raw)
    if "+" in raw:
        return "".join(_normalize_token(p) for p in _split_top_level(raw, "+"))
    return _normalize_token(raw)


def _normalize_spel(raw):
    s = raw.strip()
    if s.startswith("#{"):
        s = s[2:]
        if s.endswith("}"):
            s = s[:-1]
    s = _SPEL_VAR_RE.sub(r"{\1}", s)
    if "+" in s:
        return "".join(_normalize_token(p) for p in _split_top_level(s, "+"))
    return _normalize_token(s)


def _normalize_token(tok):
    tok = tok.strip()
    if not tok:
        return ""
    if _VAR_PLACEHOLDER_RE.fullmatch(tok):
        return tok
    m = _SPEL_VAR_RE.fullmatch(tok)
    if m:
        return "{" + m.group(1) + "}"
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'":
        return tok[1:-1]
    if _UPPER_CONST_RE.fullmatch(tok):
        return tok
    if _IDENT_RE.fullmatch(tok):
        return "{" + tok + "}"
    return tok


def _split_top_level(s, sep):
    parts = []
    buf = []
    in_str = None
    i = 0
    while i < len(s):
        c = s[i]
        if in_str:
            buf.append(c)
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in "\"'":
            in_str = c
            buf.append(c)
            i += 1
            continue
        if s.startswith(sep, i):
            parts.append("".join(buf))
            buf = []
            i += len(sep)
            continue
        buf.append(c)
        i += 1
    parts.append("".join(buf))
    return parts


def _find_matching_brace(content, open_idx):
    depth = 0
    for i in range(open_idx, len(content)):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _iter_methods(content):
    for m in _METHOD_SIG_RE.finditer(content):
        name = m.group("name")
        if name in _KEYWORD_FILTER:
            continue
        open_idx = m.end() - 1
        close_idx = _find_matching_brace(content, open_idx)
        if close_idx == -1:
            continue
        yield name, m.start(), open_idx, close_idx


def _parse_annotation_args(args):
    if not args:
        return {}
    attrs = {}
    for m in _ATTR_RE.finditer(args):
        key = m.group(1)
        val = m.group(2).strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        attrs[key] = val
    return attrs


def _as_var_name(s):
    s = s.strip().strip('"').strip("'")
    s = re.sub(r"^#\{?", "", s)
    return s.rstrip("}")


def _annotation_pattern(attrs):
    prefix = attrs.get("prefix", "")
    keypath = attrs.get("keyPath")
    key = attrs.get("key")
    value = attrs.get("value")
    if keypath is not None:
        var = _as_var_name(keypath)
        return f"{prefix}:{{{var}}}" if prefix else f"{{{var}}}"
    keyval = key if key is not None else value
    if keyval is None:
        return prefix or ""
    norm = normalize_key_pattern(keyval)
    if prefix and norm:
        return f"{prefix}:{norm}"
    return norm or prefix


def _find_annotations(pre_text):
    results = []
    for m in _ANNOTATION_RE.finditer(pre_text):
        name = m.group(1)
        kind = _ANNOTATION_NAME_TO_KIND.get(name)
        if kind is None:
            continue
        attrs = _parse_annotation_args(m.group(2))
        pattern = _annotation_pattern(attrs)
        if not pattern:
            continue
        results.append((kind, pattern, _extract_variables(pattern)))
    return results


def _find_method_calls(body):
    results = []
    for m in _LOCK_CALL_RE.finditer(body):
        args = m.group(2)
        first = _split_top_level(args, ",")[0].strip() if args.strip() else ""
        norm = normalize_key_pattern(first)
        if norm:
            results.append(("lock", norm, _extract_variables(norm)))
    for m in _CACHE_CALL_RE.finditer(body):
        op = m.group(2)
        args = m.group(3)
        first = _split_top_level(args, ",")[0].strip() if args.strip() else ""
        norm = normalize_key_pattern(first)
        if not norm:
            continue
        kind = "lock" if op == "setIfAbsent" else "cache"
        results.append((kind, norm, _extract_variables(norm)))
    return results


def _find_shards(body):
    results = []
    for m in _SHARD_RE.finditer(body):
        var = m.group(1)
        results.append((f"{{{var}}}", [var]))
    return results


def _extract_variables(pattern):
    return _VAR_PLACEHOLDER_RE.findall(pattern)


def extract_key_templates(java_files):
    results = []
    counter = 1
    for jf in java_files:
        content = jf.content
        class_name = getattr(jf, "class_name", "")
        for name, sig_start, body_start, body_end in _iter_methods(content):
            desc = extract_method_doc(content, sig_start)
            pre_start = content.rfind("}", 0, sig_start) + 1
            pre = content[pre_start:sig_start]
            body = content[body_start:body_end]
            for kind, pattern, variables in _find_annotations(pre):
                results.append(_make_entry(counter, kind, class_name, name, pattern, variables, desc))
                counter += 1
            for kind, pattern, variables in _find_method_calls(body):
                results.append(_make_entry(counter, kind, class_name, name, pattern, variables, desc))
                counter += 1
            for pattern, variables in _find_shards(body):
                results.append(_make_entry(counter, "shard", class_name, name, pattern, variables, desc))
                counter += 1
    return results


def _make_entry(counter, kind, class_name, method_name, pattern, variables, desc):
    return {
        "id": "KEY-%03d" % counter,
        "kind": kind,
        "class_name": class_name,
        "method_name": method_name,
        "pattern": pattern,
        "variables": ",".join(variables),
        "business_desc": desc,
    }
