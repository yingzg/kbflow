"""确定性工具命令，供 AI IDE 通过 md Prompt 调用。

这些命令只做确定性事实处理；语义由 AI 完成。读路径：AI 直接读 .toon（省 token）。
写路径：AI 输出 json，用 json2toon 转 toon 落盘（AI 写 toon 易错）。
"""

import json
import sys
from pathlib import Path

from kbflow.toon import toon_dumps, toon_loads
from kbflow.stages.k01_scan import run_scan, ScanError
from kbflow.stages.k02_divide import build_boundary_matrix, load_entries
from kbflow.stages.k03_confirm import (
    apply_decision,
    classify_by_score,
    markdown_to_reviews,
    reviews_to_markdown,
)
from kbflow.stages.k04_knowledge import (
    generate_data_model_skeleton,
    generate_interface_skeleton,
    generate_overview_skeleton,
)
from kbflow.stages.k05_cross import build_cross_service_links, build_domain_overview
from kbflow.stages.k06_meta import build_dev_standards, build_service_meta, build_tech_config
from kbflow.stages.k07_index import generate_panorama_md
from kbflow.stages.k08_narrate import seal_facts


def _fail(msg):
    print("❌ %s" % msg, file=sys.stderr)
    return 1


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_toon(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(toon_dumps(data), encoding="utf-8")
    print("✅ 已写入 %s" % p)


def cmd_json2toon(args):
    """AI 输出 json → 转 toon 落盘。写路径唯一入口，避免 AI 手写 toon 出错。"""
    data = _read_json(args.json_file)
    if args.wrap:
        data = {args.wrap: data}
    _write_toon(args.out, data)
    return 0


def cmd_matrix(args):
    """读领域建议（domains 列表），生成边界矩阵（带 D1/D2.. id）。"""
    doc = toon_loads(Path(args.domains).read_text(encoding="utf-8"))
    domains = doc.get("domains", []) if isinstance(doc, dict) else []
    matrix = build_boundary_matrix(domains)
    _write_toon(args.out, {"domain_boundary_matrix": matrix})
    return 0


def cmd_checklist_gen(args):
    """读 AI 评分结果（reviews），筛出低置信度，生成人工复核清单 md。"""
    doc = toon_loads(Path(args.reviews).read_text(encoding="utf-8"))
    reviews = doc.get("reviews", []) if isinstance(doc, dict) else []
    threshold = getattr(args, "threshold", 70)
    low_conf = [r for r in reviews if classify_by_score(r.get("score", 0), threshold) == "review"]
    Path(args.out).write_text(reviews_to_markdown(low_conf), encoding="utf-8")
    print("✅ 已生成复核清单 %s（%d 条低置信度）" % (args.out, len(low_conf)))
    return 0


def cmd_checklist_parse(args):
    """读人工改过的复核清单 md，解析决定，生成 review_decisions.toon。"""
    text = Path(args.checklist).read_text(encoding="utf-8")
    reviews = markdown_to_reviews(text)
    decisions = [apply_decision(r) for r in reviews]
    _write_toon(args.out, {"reviews": decisions})
    return 0


def _load_facts(output):
    """从 output/service-meta/ 读事实文件。"""
    meta = Path(output) / "service-meta"
    facts = {}
    if (meta / "behavior.toon").exists():
        facts["behavior"] = toon_loads((meta / "behavior.toon").read_text(encoding="utf-8"))
    if (meta / "topology.toon").exists():
        facts["topology"] = toon_loads((meta / "topology.toon").read_text(encoding="utf-8"))
    if (meta / "ddl.toon").exists():
        facts["ddl"] = toon_loads((meta / "ddl.toon").read_text(encoding="utf-8"))
    if (meta / "mapper_tables.toon").exists():
        mt = toon_loads((meta / "mapper_tables.toon").read_text(encoding="utf-8"))
        facts["mapper_tables"] = {
            m["mapper"]: m["tables"].split("|")
            for m in mt.get("mapper_tables", [])
        }
    if (meta / "external_dependencies.toon").exists():
        facts["external"] = toon_loads((meta / "external_dependencies.toon").read_text(encoding="utf-8"))
    if (meta / "domain_division.toon").exists():
        facts["division"] = toon_loads((meta / "domain_division.toon").read_text(encoding="utf-8"))
    return facts


def _domain_entries(facts, domain_name, output):
    """读 behavior.toon 全部入口，按 domain_mapping 过滤出该领域入口。"""
    meta = Path(output) / "service-meta"
    entries = load_entries(meta)
    division = facts.get("division", {})
    mapping = division.get("domain_mapping", [])
    matrix = division.get("domain_boundary_matrix", [])
    ref_to_name = {d["id"]: d["name"] for d in matrix}
    ref_of = {m["entry_id"]: m["domain_ref"] for m in mapping}
    name_to_ref = {d["name"]: d["id"] for d in matrix}
    target_ref = name_to_ref.get(domain_name)
    return [
        e for e in entries
        if ref_to_name.get(ref_of.get(e["id"], "D99")) == domain_name
        or (target_ref is not None and ref_of.get(e["id"]) == target_ref)
    ]


def cmd_skeleton(args):
    output = args.output
    facts = _load_facts(output)
    domain = args.domain
    service = args.service

    entries = _domain_entries(facts, domain, output)
    topology = facts.get("topology", {})
    tables = facts.get("ddl", {}).get("tables", [])
    mapper_tables = facts.get("mapper_tables", {})
    division = facts.get("division", {})
    matrix = division.get("domain_boundary_matrix", [])
    mapping = division.get("domain_mapping", [])

    kind = args.kind

    if kind == "overview":
        out = Path(output) / domain / service / "01-服务概述.toon"
        data = generate_overview_skeleton(domain, service, entries)
    elif kind == "interface":
        out = Path(output) / domain / service / "02-接口链路.toon"
        data = generate_interface_skeleton(entries, topology, tables, mapper_tables)
    elif kind == "data-model":
        out = Path(output) / domain / service / "03-数据模型.toon"
        interface = generate_interface_skeleton(entries, topology, tables, mapper_tables)
        data = generate_data_model_skeleton(tables, interface["entry_tables"], entries)
    elif kind == "domain-overview":
        out = Path(output) / domain / "01-领域总览.toon"
        data = build_domain_overview(domain, service, entries)
    elif kind == "cross-links":
        out = Path(output) / domain / "02-跨服务链路.toon"
        data = build_cross_service_links(entries, topology, service)
    elif kind == "service-meta":
        out = Path(output) / service / "service-meta" / "服务元信息.toon"
        data = build_service_meta(service, entries, matrix, mapping)
    elif kind == "tech-config":
        out = Path(output) / service / "service-meta" / "技术配置.toon"
        mavens = facts.get("external", {}).get("mavens", {})
        data = build_tech_config(mavens)
    elif kind == "dev-standards":
        out = Path(output) / service / "service-meta" / "开发规范.toon"
        data = build_dev_standards(entries)
    else:
        return _fail("未知骨架类型: %s（可选: overview/interface/data-model/domain-overview/cross-links/service-meta/tech-config/dev-standards）" % kind)

    _write_toon(out, data)
    return 0


def cmd_seal(args):
    """把该领域的事实密封成结构化清单，供 AI 写自然语言叙述时引用。"""
    meta = Path(args.output) / "service-meta"
    facts = _load_facts(args.output)
    entries = _domain_entries(facts, args.domain, args.output)
    tables = facts.get("ddl", {}).get("tables", [])
    sealed = seal_facts(args.domain, args.service, entries, tables)
    if args.out:
        _write_toon(args.out, sealed)
    else:
        print(json.dumps(sealed, ensure_ascii=False))
    return 0


def cmd_panorama(args):
    doc = toon_loads(Path(args.matrix).read_text(encoding="utf-8"))
    matrix = doc.get("domain_boundary_matrix", []) if isinstance(doc, dict) else []
    md = generate_panorama_md(matrix, args.service)
    Path(args.out).write_text(md, encoding="utf-8")
    print("✅ 已生成全景图 %s" % args.out)
    return 0


def cmd_scan(args):
    try:
        result = run_scan(args.project, args.output)
    except ScanError as e:
        return _fail(str(e))
    print("✅ 扫描完成：%d 个入口" % result["entry_count"])
    for w in result["warnings"]:
        print("⚠ %s" % w)
    return 0
