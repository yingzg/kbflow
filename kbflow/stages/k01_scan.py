from pathlib import Path

from kbflow.gates.completeness import check_count_conservation
from kbflow.gates.self_check import check_declared_counts
from kbflow.scanners.behavior import scan_behavior
from kbflow.scanners.comment_category import categorize
from kbflow.scanners.ddl import extract_tables
from kbflow.scanners.dependency import scan_external_dependencies
from kbflow.scanners.file_index import FileIndex
from kbflow.scanners.key_template import extract_key_templates
from kbflow.scanners.sql_tables import extract_mapper_tables
from kbflow.scanners.topology import scan_topology
from kbflow.toon import toon_dumps


def _assign_ids(entries, counter, prefix="API"):
    result = []
    for e in entries:
        eid = "%s-%03d" % (prefix, counter[0])
        counter[0] += 1
        e["id"] = eid
        result.append(e)
    return result


class ScanError(Exception):
    pass


def run_scan(project_dir, output_dir, verbose=True):
    project_dir = Path(project_dir)
    output_dir = Path(output_dir)
    meta_dir = output_dir / "service-meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    def _step(name):
        if verbose:
            print("  %s ..." % name, flush=True)

    def _guard(name, fn):
        _step(name)
        try:
            return fn()
        except ScanError:
            raise
        except Exception as e:
            raise ScanError("K01 扫描失败于「%s」: %s" % (name, e)) from e

    def _progress(n):
        if verbose:
            print("    已扫描 %d 个 Java 文件..." % n, flush=True)

    index = _guard("扫描 Java 文件", lambda: FileIndex(project_dir, on_progress=_progress))
    if verbose:
        print("    ✓ 发现 %d 个 Java 文件" % len(index.all_files()), flush=True)

    prefixes = _guard("推断内部包前缀", lambda: index.internal_prefixes())
    if verbose:
        print("    ✓ 内部前缀: %s" % ", ".join(prefixes), flush=True)

    behavior = _guard("发现业务入口 (Dubbo/REST/MQ/Job)", lambda: scan_behavior(index))
    if verbose:
        total = sum(len(behavior[k]) for k in ("dubbo", "rest", "mq", "job"))
        print("    ✓ 发现 %d 个业务入口" % total, flush=True)

    deps = _guard("分析外部依赖", lambda: scan_external_dependencies(index, prefixes))
    topo = _guard("构建依赖拓扑", lambda: scan_topology(index, behavior, prefixes))
    keys = _guard("提取 Key 模板", lambda: extract_key_templates(index.all_files()))
    mapper_tables = _guard("提取 Mapper 表名", lambda: extract_mapper_tables(index))

    def _scan_ddl():
        from kbflow.config import get_database_config
        from kbflow.db.database_source import read_tables_from_mcp

        db_cfg = get_database_config()
        if db_cfg.get("mcp_command"):
            args = db_cfg.get("mcp_args", "").split() if db_cfg.get("mcp_args") else []
            try:
                tables = read_tables_from_mcp(
                    db_cfg["mcp_command"], args, db_cfg.get("env", {}), db_cfg.get("mcp_cwd") or None
                )
                if tables:
                    return tables
            except Exception as e:
                if verbose:
                    print("    ⚠ 数据库 MCP 读取失败，回退到 .sql: %s" % e, flush=True)
        tables = []
        for sql in project_dir.rglob("*.sql"):
            tables.extend(extract_tables(sql.read_text(encoding="utf-8", errors="replace")))
        return tables

    ddl_tables = _guard("提取表结构", _scan_ddl)

    counter = [1]
    discovered = 0
    for kind in ("dubbo", "rest", "mq", "job"):
        behavior[kind] = _assign_ids(behavior[kind], counter)
        discovered += len(behavior[kind])

    for e in behavior["dubbo"] + behavior["rest"] + behavior["mq"] + behavior["job"]:
        categorize([e])

    artifacts = {
        "behavior": _build_behavior_doc(behavior),
        "external_dependencies": deps,
        "topology": topo,
        "ddl": {"tables": ddl_tables},
        "key_templates": {"key_templates": keys},
        "mapper_tables": {
            "mapper_tables": [
                {"mapper": m, "tables": "|".join(ts)}
                for m, ts in sorted(mapper_tables.items())
            ]
        },
    }

    warnings = []
    for name, doc in artifacts.items():
        _step("生成 %s.toon" % name)
        try:
            text = toon_dumps(doc)
        except Exception as e:
            raise ScanError("序列化产物「%s」失败: %s" % (name, e)) from e
        fixed, fixes = check_declared_counts(text)
        if fixes:
            warnings.append("self_check 修复 %s: %s" % (name, fixes))
            text = fixed
        (meta_dir / (name + ".toon")).write_text(text, encoding="utf-8")

    entry_ids = [e["id"] for e in behavior["dubbo"] + behavior["rest"] + behavior["mq"] + behavior["job"]]
    gate = check_count_conservation(discovered, len(entry_ids), "入口完整性")
    gate.raise_if_blocked()

    return {
        "project": project_dir.name,
        "internal_prefixes": prefixes,
        "entry_count": discovered,
        "warnings": warnings,
        "artifacts": list(artifacts.keys()),
    }


def _methods_to_str(methods):
    parts = []
    for m in methods:
        if m.get("doc"):
            parts.append("%s(%s)" % (m["name"], m["doc"]))
        else:
            parts.append(m["name"])
    return ";".join(parts)


def _build_behavior_doc(behavior):
    doc = {"metadata": {"entry_count": 0}}
    total = 0
    for kind in ("dubbo", "rest", "mq", "job"):
        entries = behavior[kind]
        doc[kind] = {"with_doc": [], "no_doc": []}
        for e in entries:
            total += 1
            has_doc = bool(e.get("doc")) or any(m.get("doc") for m in e.get("methods", []))
            bucket = "with_doc" if has_doc else "no_doc"
            doc[kind][bucket].append({
                "id": e["id"],
                "class_name": e["class_name"],
                "package": e.get("package", ""),
                "doc": e.get("doc", ""),
                "methods": _methods_to_str(e.get("methods", [])),
            })
    doc["metadata"]["entry_count"] = total
    return doc
