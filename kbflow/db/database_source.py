from kbflow.db.mcp_client import McpClient, _extract_text, _parse_table_names


def read_tables_from_mcp(command, args, env, cwd):
    client = McpClient(command, args, env, cwd)
    try:
        result = client.call_tool("list_tables")
        text = _extract_text(result)
        table_names = _parse_table_names(text)
        if not table_names:
            raw = result.get("tables") or result.get("tableNames") or []
            table_names = [
                (t if isinstance(t, str) else t.get("name", ""))
                for t in raw
                if (t if isinstance(t, str) else t.get("name"))
            ]
        ddl_tables = []
        for name in table_names:
            ddl = _fetch_table_ddl(client, name)
            ddl_tables.append({"name": name, "ddl": ddl})
        return ddl_tables
    finally:
        client.close()


def _fetch_table_ddl(client, table_name):
    try:
        result = client.call_tool("execute_sql", {"sql": "SHOW CREATE TABLE %s" % table_name})
        text = _extract_text(result)
        if text:
            return text.strip()
    except Exception:
        pass
    return ""
