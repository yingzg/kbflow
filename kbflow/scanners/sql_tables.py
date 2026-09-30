import re

_SQL_TABLE_RE = re.compile(r"\b(?:FROM|INTO|UPDATE|JOIN)\s+([`\"\[]?[\w.$]+[`\"\]]?)", re.IGNORECASE)
_SQL_KEYWORDS = {
    "dual", "where", "select", "set", "values", "and", "or", "on", "as", "id",
    "value", "name", "type", "count", "sum", "min", "max", "avg",
    "inner", "left", "right", "outer", "cross", "full", "group", "order", "by",
    "having", "limit", "offset", "union", "all", "distinct", "case", "when",
    "then", "else", "end", "exists", "not", "null", "is", "in", "like", "between",
    "key", "primary", "foreign", "index", "table", "view",
}


def extract_tables_from_sql(sql_text):
    tables = set()
    for t in _SQL_TABLE_RE.finditer(sql_text):
        name = t.group(1).strip("`\"[]")
        if name and name.lower() not in _SQL_KEYWORDS and not name.lower().startswith("from"):
            tables.add(name)
    return tables


def extract_tables_from_annotations(content):
    tables = set()
    for m in re.finditer(r"@(?:Select|Insert|Update|Delete)\s*\(\s*\"([^\"]+)\"", content, re.IGNORECASE | re.DOTALL):
        tables.update(extract_tables_from_sql(m.group(1)))
    return tables


def extract_tables_from_xml(content):
    tables = set()
    for m in re.finditer(
        r"<(?:select|insert|update|delete)[^>]*>(.*?)</(?:select|insert|update|delete)>",
        content, re.IGNORECASE | re.DOTALL,
    ):
        tables.update(extract_tables_from_sql(m.group(1)))
    return tables


def extract_mapper_tables(index):
    result = {}
    for f in index.all_files():
        if f.class_name.endswith("Mapper") or "@Mapper" in f.content:
            tables = extract_tables_from_annotations(f.content)
            if tables:
                result[f.class_name] = tables
    for xml_path in index.project_dir.rglob("*.xml"):
        content = xml_path.read_text(encoding="utf-8", errors="replace")
        ns = re.search(r'<mapper[^>]*namespace="([^"]+)"', content)
        if not ns:
            continue
        mapper_class = ns.group(1).split(".")[-1]
        tables = extract_tables_from_xml(content)
        if tables:
            result.setdefault(mapper_class, set()).update(tables)
    return {k: sorted(v) for k, v in result.items()}
