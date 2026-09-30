import re

_ANCHOR_RE = re.compile(r"^\s*--\s*TABLE\s*:\s*(\S+)", re.IGNORECASE)
_CREATE_TABLE_RE = re.compile(
    r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?P<name>[\w`\"$.]+)"
    r"(?P<body>.*?;)",
    re.IGNORECASE | re.DOTALL,
)


def _clean_name(name):
    return name.strip().strip("`\"'")


def _extract_create_tables(block):
    found = []
    for m in _CREATE_TABLE_RE.finditer(block):
        ddl = m.group(0).strip()
        found.append((_clean_name(m.group("name")), ddl))
    return found


def extract_tables(ddl_text):
    lines = ddl_text.splitlines()
    sections = []
    current_anchor = None
    current_lines = []
    for line in lines:
        m = _ANCHOR_RE.match(line)
        if m:
            sections.append((current_anchor, current_lines))
            current_anchor = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    sections.append((current_anchor, current_lines))

    tables = []
    for anchor, block_lines in sections:
        block = "\n".join(block_lines)
        creates = _extract_create_tables(block)
        if anchor is not None:
            if creates:
                _, ddl = creates[0]
                tables.append({"name": anchor, "ddl": ddl})
        else:
            for name, ddl in creates:
                tables.append({"name": name, "ddl": ddl})
    return tables
