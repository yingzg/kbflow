import argparse
import sys
from pathlib import Path

from kbflow.config import get_llm_config
from kbflow.llm import LLMError, LLMNotConfiguredError, require_llm
from kbflow.stages.k01_scan import ScanError, run_scan
from kbflow.stages.k02_divide import (
    build_boundary_matrix,
    classify_entries,
    domains_to_toon,
    load_entries,
    suggest_domains,
    toon_to_domains,
)
from kbflow.stages.k03_confirm import (
    apply_decision,
    classify_by_score,
    markdown_to_reviews,
    reviews_to_markdown,
    score_entries_batch,
    score_entry,
)
from kbflow.stages.k04_knowledge import (
    enrich_overview,
    generate_data_model_skeleton,
    generate_interface_skeleton,
    generate_overview_skeleton,
)
from kbflow.stages.k05_cross import build_cross_service_links, build_domain_overview, enrich_domain_overview
from kbflow.stages.k06_meta import (
    build_dev_standards,
    build_service_meta,
    build_tech_config,
    enrich_service_meta,
)
from kbflow.stages.k07_index import generate_panorama_md
from kbflow.stages.k08_narrate import seal_facts, generate_glossary, narrate
from kbflow.sync.sync_kb import sync_to_kb
from kbflow.toon import toon_dumps, toon_loads


def _meta_dir(output):
    return Path(output) / "service-meta"


def _domain_to_ref(matrix, domain_name):
    for d in matrix:
        if d["name"] == domain_name:
            return d["id"]
    return "D99"


def _cmd_config(args):
    import configparser

    cfg_dir = Path.home() / ".kbflow"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "config.ini"

    print("\nKBFlow 配置向导\n")

    print("【1/2】LLM 配置（K02 起需要）")
    api_key = input("  API Key（必填）: ").strip()
    if not api_key:
        print("  ❌ API Key 不能为空，未写入配置")
        return 1
    base_url = input("  Base URL [https://api.openai.com/v1]: ").strip()
    if not base_url:
        base_url = "https://api.openai.com/v1"
    model = input("  Model [gpt-4o-mini]: ").strip()
    if not model:
        model = "gpt-4o-mini"

    print("\n【2/2】数据库配置（可选，K01 读真实表结构用；直接回车跳过）")
    mcp_command = input("  MCP 命令（如 ./toolbox）[回车跳过]: ").strip()
    db_section = {}
    db_env = {}
    if mcp_command:
        mcp_args = input("  MCP 参数（如 --prebuilt oceanbase --stdio）: ").strip()
        mcp_cwd = input("  MCP 工作目录（如 /root/.codex）: ").strip()
        db_type = input("  数据库类型 [oceanbase/mssql]: ").strip().lower()
        if db_type not in ("oceanbase", "mssql"):
            db_type = "oceanbase"
        prefix = "OCEANBASE" if db_type == "oceanbase" else "MSSQL"
        db_name = input("  数据库名: ").strip()
        db_host = input("  主机: ").strip()
        db_port = input("  端口: ").strip()
        db_user = input("  用户名: ").strip()
        db_password = input("  密码: ").strip()
        db_section = {"mcp_command": mcp_command, "mcp_args": mcp_args, "mcp_cwd": mcp_cwd}
        db_env = {
            prefix + "_DATABASE": db_name,
            prefix + "_HOST": db_host,
            prefix + "_PORT": db_port,
            prefix + "_USER": db_user,
            prefix + "_PASSWORD": db_password,
        }

    parser = configparser.ConfigParser()
    parser["llm"] = {"api_key": api_key, "base_url": base_url, "model": model}
    if mcp_command:
        parser["database"] = db_section
        parser["database.env"] = db_env
    with open(cfg_path, "w", encoding="utf-8") as f:
        parser.write(f)
    print("\n✅ 配置已写入 %s" % cfg_path)
    print("  现在可运行: python kbflow.py run <项目路径> -o <输出目录>")
    return 0


def _step_header(i, title):
    print("\n━━━━━ [%d/8] %s ━━━━━" % (i, title))


def _press_enter(auto, hint="按 Enter 继续下一步"):
    if auto:
        return True
    resp = input("  %s，输入 q 退出: " % hint).strip().lower()
    return resp != "q"


def _cmd_run(args):
    project = args.project
    output = args.output
    auto = args.auto
    service_name = Path(project).name
    meta = _meta_dir(output)

    print("\n╔══════════════════════════════════════╗")
    print("║      KBFlow 知识库构建向导          ║")
    print("╚══════════════════════════════════════╝")
    print("\n项目: %s\n输出: %s\n" % (project, output))

    _step_header(1, "K01 事实扫描")
    if (meta / "behavior.toon").exists() and (meta / "mapper_tables.toon").exists():
        print("  ⏭ 已跳过（K01 产物已存在，断点续跑）")
    else:
        if (meta / "behavior.toon").exists():
            print("  ⚠ K01 产物是旧版本（缺 mapper_tables），重新扫描补全")
        try:
            result = run_scan(project, output)
        except ScanError as e:
            print("  ❌ %s" % e)
            print("  已生成的部分产物保留在 %s/" % output)
            return 1
        print("  ✅ 发现 %d 个业务入口" % result["entry_count"])
        for w in result["warnings"]:
            print("  ⚠ %s" % w)
    entries = load_entries(meta)
    if not entries:
        print("  ❌ 未发现业务入口，请确认项目路径")
        return 1
    if not _press_enter(auto):
        return 0

    _step_header(2, "K02 领域划分（LLM）")
    division_path = meta / "domain_division.toon"
    if division_path.exists():
        print("  ⏭ 已跳过（domain_division.toon 已存在，断点续跑）")
        division = toon_loads(division_path.read_text(encoding="utf-8"))
        matrix = division.get("domain_boundary_matrix", [])
        domains = [{"name": d["name"]} for d in matrix]
    else:
        try:
            llm = require_llm()
        except LLMNotConfiguredError as e:
            print("  ❌ %s" % e)
            print("  （K01 已完成，产物在 %s/service-meta/）" % output)
            return 1
        signals = [
            {"id": e["id"], "class_name": e["class_name"], "package": e["package"],
             "doc": e["doc"], "methods": e["methods"]}
            for e in entries
        ]
        print("  🤖 正在调用 LLM 分析 %d 个业务入口生成领域建议（可能耗时 30-60 秒，请稍候）..." % len(signals), flush=True)
        domains = suggest_domains(llm, signals)
        print("  ✓ LLM 返回 %d 个领域建议" % len(domains), flush=True)

        suggestion_path = meta / "domain_suggestion.toon"
        suggestion_path.write_text(domains_to_toon(domains), encoding="utf-8")
        print("  📄 领域建议清单已写入: %s" % suggestion_path)
        print("     （每行一个领域，字段依次：领域名 / 职责 / 关键实体 / 边界包含 / 边界排除）")
        if auto:
            print("  ⏭ --auto 模式：直接采纳 LLM 建议")
        else:
            print("  请打开该文件检查修改（改领域名、增删领域），改完后回来按 Enter 继续")
            resp = input("  改完按 Enter 继续，输入 q 退出: ").strip().lower()
            if resp == "q":
                return 0
            try:
                domains = toon_to_domains(suggestion_path.read_text(encoding="utf-8"))
            except Exception as e:
                print("  ❌ 读取领域清单失败（格式可能被改坏）: %s" % e)
                print("  请检查 %s，重新运行本阶段" % suggestion_path)
                return 1
            print("  ✓ 已读取修改后的领域清单（%d 个领域）" % len(domains))

        matrix = build_boundary_matrix(domains)

        print("  🤖 正在把 %d 个业务入口分类到 %d 个领域（批量调 LLM，约 1-3 分钟）..." % (len(entries), len(domains)), flush=True)
        classifications = classify_entries(llm, entries, domains)
        domain_id = {d["name"]: d["id"] for d in matrix}
        mapping = []
        for c in classifications:
            entry_id = c.get("entry_id", "")
            domain_name = c.get("domain", "")
            domain_ref = domain_id.get(domain_name, "D99")
            mapping.append({
                "entry_id": entry_id,
                "domain_ref": domain_ref,
                "reason": c.get("reason", ""),
            })
        print("  ✓ 已分类 %d 个入口" % len(mapping), flush=True)

        division = {
            "domain_boundary_matrix": matrix,
            "domain_mapping": mapping,
        }
        (meta / "domain_division.toon").write_text(toon_dumps(division), encoding="utf-8")
        (meta / "domain_boundary_matrix.toon").write_text(
            toon_dumps({"domain_boundary_matrix": matrix}), encoding="utf-8")
        print("  ✅ 领域划分完成：%d 个领域，%d 个入口已归属" % (len(matrix), len(mapping)))
    if not _press_enter(auto):
        return 0

    _step_header(3, "K03 边界确认（LLM 四维评分）")
    if (meta / "review_decisions.toon").exists():
        print("  ⏭ 已跳过（复核决策已存在，断点续跑）")
    else:
        try:
            llm = require_llm()
        except LLMNotConfiguredError as e:
            print("  ❌ %s" % e)
            return 1
        batch_count = (len(entries) + 24) // 25
        if batch_count > 1:
            print("  🤖 正在并发评分 %d 个入口（%d 批并发调 LLM，约 1-3 分钟）..." % (len(entries), batch_count), flush=True)
        else:
            print("  🤖 正在评分 %d 个入口..." % len(entries), flush=True)

        batch_reviews = score_entries_batch(llm, entries, matrix)
        review_map = {r.get("entry_id"): r for r in batch_reviews}
        accepted = []
        low_conf = []
        for e in entries:
            r = review_map.get(e["id"], {})
            review = {
                "entry_id": e["id"],
                "class_name": e["class_name"],
                "score": r.get("score", 0),
                "suggested": r.get("decision", "KEEP"),
                "target_domain": r.get("target_domain", ""),
                "decision": "",
                "reason": r.get("reason", ""),
            }
            if classify_by_score(review["score"]) == "review":
                low_conf.append(review)
            else:
                accepted.append(apply_decision(review))
        print("  ✓ 评分完成：%d 个自动采纳，%d 个低置信度待人工复核" % (len(accepted), len(low_conf)), flush=True)

        decisions = list(accepted)
        if low_conf:
            review_path = meta / "review_checklist.md"
            review_path.write_text(reviews_to_markdown(low_conf), encoding="utf-8")
            print("  📄 低置信度复核清单已写入: %s" % review_path)
            print("     （每条填「最终决定」：留空=采纳建议；KEEP / MOVE / MOVE:领域名 / DELETE）")
            if auto:
                print("  ⏭ --auto 模式：低置信度条目按 LLM 建议处理")
                for r in low_conf:
                    decisions.append(apply_decision(r))
            else:
                print("  请打开该文件填写「最终决定」，保存后回来按 Enter 继续")
                resp = input("  改完按 Enter 继续，输入 q 退出: ").strip().lower()
                if resp == "q":
                    return 0
                reviewed = markdown_to_reviews(review_path.read_text(encoding="utf-8"))
                for r in reviewed:
                    decisions.append(apply_decision(r))
                print("  ✓ 已读取人工复核结果（%d 条）" % len(reviewed))

        (meta / "review_decisions.toon").write_text(
            toon_dumps({"reviews": decisions}), encoding="utf-8")
        print("  ✅ 复核决策已生成（共 %d 条）" % len(decisions))

        if (meta / "domain_division.toon").exists():
            division = toon_loads((meta / "domain_division.toon").read_text(encoding="utf-8"))
            mapping = division.get("domain_mapping", [])
            decision_map = {d["entry_id"]: d for d in decisions}
            for m in mapping:
                d = decision_map.get(m["entry_id"])
                if not d:
                    continue
                if d["decision"] == "MOVE" and d.get("domain"):
                    m["domain_ref"] = _domain_to_ref(matrix, d["domain"])
                elif d["decision"] == "DELETE":
                    m["domain_ref"] = "D99"
            division["domain_mapping"] = mapping
            (meta / "domain_division.toon").write_text(toon_dumps(division), encoding="utf-8")
            print("  ✅ 决策已回写 domain_division.toon")
    if not _press_enter(auto):
        return 0

    _step_header(4, "K04 领域知识（3 份文档）")
    topology = toon_loads((meta / "topology.toon").read_text(encoding="utf-8"))
    tables = toon_loads((meta / "ddl.toon").read_text(encoding="utf-8")).get("tables", [])
    mapper_tables = {}
    if (meta / "mapper_tables.toon").exists():
        mt_doc = toon_loads((meta / "mapper_tables.toon").read_text(encoding="utf-8")).get("mapper_tables", [])
        mapper_tables = {m["mapper"]: m["tables"].split("|") for m in mt_doc}
    division = toon_loads((meta / "domain_division.toon").read_text(encoding="utf-8"))
    mapping = division.get("domain_mapping", [])
    entry_domain = {m["entry_id"]: m["domain_ref"] for m in mapping}
    ref_to_name = {d["id"]: d["name"] for d in matrix}
    entries_by_domain = {}
    for e in entries:
        ref = entry_domain.get(e["id"], "D99")
        name = ref_to_name.get(ref, "unclassified")
        entries_by_domain.setdefault(name, []).append(e)

    llm = None
    try:
        llm = require_llm()
    except LLMNotConfiguredError:
        print("  ⚠ 未配置 LLM，K04 只生成骨架（语义字段留 [待AI补充]）")

    for d in domains:
        domain_entries = entries_by_domain.get(d["name"], [])
        out = Path(output) / d["name"] / service_name
        out.mkdir(parents=True, exist_ok=True)
        overview = generate_overview_skeleton(d["name"], service_name, domain_entries)
        if llm is not None:
            print("  🤖 正在补「%s」领域服务概述语义..." % d["name"], flush=True)
            overview = enrich_overview(llm, d["name"], service_name, overview, domain_entries)
        interface = generate_interface_skeleton(domain_entries, topology, tables, mapper_tables)
        data_model = generate_data_model_skeleton(tables, interface["entry_tables"], domain_entries)
        (out / "01-服务概述.toon").write_text(toon_dumps(overview), encoding="utf-8")
        (out / "02-接口链路.toon").write_text(toon_dumps(interface), encoding="utf-8")
        (out / "03-数据模型.toon").write_text(toon_dumps(data_model), encoding="utf-8")
    print("  ✅ 已为 %d 个领域生成 3 份文档（每个领域只含其归属入口）" % len(domains))
    if not _press_enter(auto):
        return 0

    _step_header(5, "K05 跨服务链路")
    topology = toon_loads((meta / "topology.toon").read_text(encoding="utf-8"))
    for d in domains:
        domain_entries = entries_by_domain.get(d["name"], [])
        out = Path(output) / d["name"]
        out.mkdir(parents=True, exist_ok=True)
        overview = build_domain_overview(d["name"], service_name, domain_entries)
        if llm is not None:
            print("  🤖 正在补「%s」领域总览语义..." % d["name"], flush=True)
            overview = enrich_domain_overview(llm, d["name"], overview, domain_entries)
        links = build_cross_service_links(domain_entries, topology, service_name)
        (out / "01-领域总览.toon").write_text(toon_dumps(overview), encoding="utf-8")
        (out / "02-跨服务链路.toon").write_text(toon_dumps(links), encoding="utf-8")
    print("  ✅ 已为 %d 个领域生成领域总览 + 跨服务链路" % len(domains))
    if not _press_enter(auto):
        return 0

    _step_header(6, "K06 服务元信息（3 份文档）")
    division = toon_loads((meta / "domain_division.toon").read_text(encoding="utf-8"))
    mapping = division.get("domain_mapping", [])
    deps_doc = toon_loads((meta / "external_dependencies.toon").read_text(encoding="utf-8"))
    mavens = deps_doc.get("mavens", {})
    out = Path(output) / service_name / "service-meta"
    out.mkdir(parents=True, exist_ok=True)
    service_meta = build_service_meta(service_name, entries, matrix, mapping)
    if llm is not None:
        print("  🤖 正在补服务概述语义...", flush=True)
        service_meta = enrich_service_meta(llm, service_name, service_meta)
    tech_config = build_tech_config(mavens)
    dev_standards = build_dev_standards(entries)
    (out / "服务元信息.toon").write_text(toon_dumps(service_meta), encoding="utf-8")
    (out / "技术配置.toon").write_text(toon_dumps(tech_config), encoding="utf-8")
    (out / "开发规范.toon").write_text(toon_dumps(dev_standards), encoding="utf-8")
    print("  ✅ 服务元信息已生成（服务元信息 / 技术配置 / 开发规范）")
    if not _press_enter(auto):
        return 0

    _step_header(7, "K07 全局导航")
    domain_files = []
    service_files = []
    domain_keywords = []
    service_capabilities = []
    for d in domains:
        dname = d["name"]
        docs = []
        for doc in ("01-领域总览.toon", "02-跨服务链路.toon"):
            if (Path(output) / dname / doc).exists():
                docs.append(doc)
        domain_files.append({"domain_id": d.get("id", ""), "domain_name": dname, "path": dname, "docs": ",".join(docs)})
        files = []
        for f in ("01-服务概述.toon", "02-接口链路.toon", "03-数据模型.toon"):
            if (Path(output) / dname / service_name / f).exists():
                files.append(f)
        service_files.append({"service": service_name, "domain": dname, "path": "%s/%s" % (dname, service_name), "files": ",".join(files)})
        m = next((x for x in matrix if x["name"] == dname), {})
        domain_keywords.append({
            "domain": dname,
            "tier1_keywords": m.get("key_entities", ""),
            "tier2_keywords": m.get("boundary_included", ""),
            "anti_keywords": m.get("boundary_excluded", ""),
        })
        ov_path = Path(output) / dname / service_name / "01-服务概述.toon"
        caps = ""
        kws = ""
        if ov_path.exists():
            ov = toon_loads(ov_path.read_text(encoding="utf-8"))
            si = ov.get("service_info", {})
            caps = si.get("description", "")
            resp = si.get("core_responsibilities", [])
            if isinstance(resp, list):
                kws = ",".join(resp)
            elif resp and resp != "[待AI补充]":
                kws = resp
        service_capabilities.append({"domain": dname, "service": service_name, "capabilities": caps, "keywords": kws})

    index = {
        "services": [service_name],
        "domain_boundary_matrix": matrix,
        "domain_files": domain_files,
        "service_files": service_files,
        "domain_keywords": domain_keywords,
        "service_capabilities": service_capabilities,
    }
    (Path(output) / "ai" / "index.toon").parent.mkdir(parents=True, exist_ok=True)
    (Path(output) / "ai" / "index.toon").write_text(toon_dumps(index), encoding="utf-8")
    pano = generate_panorama_md(matrix, service_name)
    (Path(output) / "领域依赖全景图.md").write_text(pano, encoding="utf-8")
    print("  ✅ AI 索引（6 个 section）+ 全景图已生成")
    if not _press_enter(auto):
        return 0

    _step_header(8, "K08 可读性交付（glossary + 自然语言文档）")
    try:
        llm = require_llm()
    except LLMNotConfiguredError as e:
        print("  ❌ %s" % e)
        return 1
    tables = []
    if (meta / "ddl.toon").exists():
        tables = toon_loads((meta / "ddl.toon").read_text(encoding="utf-8")).get("tables", [])
    for d in domains:
        domain_entries = entries_by_domain.get(d["name"], [])
        out = Path(output) / d["name"] / service_name
        out.mkdir(parents=True, exist_ok=True)
        print("  🤖 正在为「%s」领域生成业务名词解释（批量调 LLM）..." % d["name"], flush=True)
        m = next((x for x in matrix if x["name"] == d["name"]), {})
        glossary = generate_glossary(llm, domain_entries, key_entities=m.get("key_entities", ""))
        (out / "_glossary.toon").write_text(toon_dumps({"glossary": glossary}), encoding="utf-8")
        print("  🤖 正在为「%s」领域写自然语言概述..." % d["name"], flush=True)
        facts = seal_facts(d["name"], service_name, domain_entries, tables)
        narrative = narrate(llm, facts)
        (out / "_overview.md").write_text(
            "# %s（%s）\n\n%s\n\n## 核心接口链路\n\n%s\n\n## 数据模型\n\n%s\n"
            % (service_name, d["name"], narrative,
               "\n".join("- " + c for c in facts["entries"]),
               "\n".join("- " + t for t in facts["tables"])),
            encoding="utf-8")
    print("  ✅ glossary + 自然语言文档已生成")

    print("\n╔══════════════════════════════════════╗")
    print("║          构建完成 ✅                ║")
    print("╚══════════════════════════════════════╝")
    print("\n知识库目录: %s" % output)
    print("人读文档: %s/<领域>/<服务>/_overview.md" % output)
    return 0


def _cmd_scan(args):
    try:
        result = run_scan(args.project, args.output)
    except ScanError as e:
        print("❌ %s" % e)
        return 1
    print("扫描完成: %s" % args.project)
    print("  入口数: %d" % result["entry_count"])
    print("  内部前缀: %s" % ", ".join(result["internal_prefixes"]))
    print("  产物: %s" % ", ".join(result["artifacts"]))
    for w in result["warnings"]:
        print("  ⚠ %s" % w)
    return 0


def _cmd_init(args):
    kb = Path(args.kb_dir)
    kb.mkdir(parents=True, exist_ok=True)
    projects = {"metadata": {"knowledge_base": str(kb.resolve())}, "directories": []}
    (kb / "projects.toon").write_text(toon_dumps(projects), encoding="utf-8")
    print("初始化知识库目录: %s" % kb)
    return 0


def _cmd_divide(args):
    llm = require_llm()
    meta = _meta_dir(args.output)
    entries = load_entries(meta)
    signals = [
        {"id": e["id"], "class_name": e["class_name"], "package": e["package"],
         "doc": e["doc"], "methods": e["methods"]}
        for e in entries
    ]
    domains = suggest_domains(llm, signals)
    print("LLM 建议领域: %s" % [d["name"] for d in domains])
    print("🛑 请人工确认领域清单（[Y] 采纳 / [M] 修改 / [C] 自定义）")
    print("  当前建议: %s" % ", ".join(d["name"] for d in domains))
    choice = input("确认(Y/M/C): ").strip().upper()
    if choice == "C":
        print("请手动编辑 domain_division.toon 后继续。")
        return 0
    if choice == "M":
        print("请在产物中修改领域清单后继续。")
        return 0
    matrix = build_boundary_matrix(domains)
    (meta / "domain_boundary_matrix.toon").write_text(
        toon_dumps({"domain_boundary_matrix": matrix}), encoding="utf-8")
    print("已生成 domain_boundary_matrix.toon")
    return 0


def _cmd_confirm(args):
    llm = require_llm()
    meta = _meta_dir(args.output)
    text = (meta / "behavior.toon").read_text(encoding="utf-8")
    behavior = toon_loads(text)
    entries = []
    for kind in ("dubbo", "rest", "mq", "job"):
        for bucket in ("with_doc", "no_doc"):
            for e in behavior.get(kind, {}).get(bucket, []):
                entries.append(e)
    decisions = []
    for e in entries:
        review = score_entry(llm, e, [])
        if classify_by_score(review.get("score", 0)) == "review":
            print("🛑 低置信度: %s (score=%s) 需人工复核" % (e["class_name"], review.get("score")))
            print("  建议: %s -> %s" % (review.get("decision"), review.get("target_domain", "")))
            choice = input("KEEP/MOVE/DELETE: ").strip().upper()
            if choice in ("MOVE", "DELETE"):
                review["decision"] = choice
        decisions.append(apply_decision(e, review))
    (meta / "review_decisions.toon").write_text(
        toon_dumps({"reviews": decisions}), encoding="utf-8")
    print("已生成 review_decisions.toon (%d 条)" % len(decisions))
    return 0


def _cmd_knowledge(args):
    return _hint_use_run("knowledge")


def _cmd_cross(args):
    return _hint_use_run("cross")


def _cmd_meta(args):
    return _hint_use_run("meta")


def _cmd_index(args):
    return _hint_use_run("index")


def _hint_use_run(cmd):
    print("提示：`%s` 命令已合并进 `run` 向导。请用：python kbflow.py run <项目路径> -o <输出目录>" % cmd)
    print("（run 向导会按 K01→K08 顺序推进，并支持断点续跑）")
    return 0


def _cmd_narrate(args):
    llm = require_llm()
    meta = _meta_dir(args.output)
    behavior = toon_loads((meta / "behavior.toon").read_text(encoding="utf-8"))
    entries = []
    for kind in ("dubbo", "rest", "mq", "job"):
        for bucket in ("with_doc", "no_doc"):
            for e in behavior.get(kind, {}).get(bucket, []):
                entries.append(e)
    tables = []
    if (meta / "ddl.toon").exists():
        tables = toon_loads((meta / "ddl.toon").read_text(encoding="utf-8")).get("tables", [])
    glossary = generate_glossary(llm, entries)
    facts = seal_facts(args.domain, args.service, entries, tables)
    narrative = narrate(llm, facts)
    out = Path(args.output) / args.domain / args.service
    out.mkdir(parents=True, exist_ok=True)
    (out / "_glossary.toon").write_text(toon_dumps({"glossary": glossary}), encoding="utf-8")
    (out / "_overview.md").write_text(
        "# %s（%s）\n\n%s\n\n## 核心接口链路\n\n%s\n\n## 数据模型\n\n%s\n"
        % (args.service, args.domain, narrative,
           "\n".join("- " + c for c in facts["entries"]),
           "\n".join("- " + t for t in facts["tables"])),
        encoding="utf-8")
    print("已生成 glossary + 自然语言文档")
    return 0


def _cmd_sync(args):
    framework_dir = Path(__file__).resolve().parent.parent
    report = sync_to_kb(framework_dir, args.kb_dir, strict=args.strict)
    print("同步完成")
    if report["orphans"]:
        print("孤儿文件（报告不删）:")
        for name, files in report["orphans"].items():
            for f in files:
                print("  - %s/%s" % (name, f))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kbflow", description="代码知识库构建工具")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("init", help="初始化知识库目录")
    p.add_argument("kb_dir", nargs="?", default="kb")

    p = sub.add_parser("run", help="交互式向导（推荐）：一步下一步构建完整知识库")
    p.add_argument("project", help="Java 项目路径")
    p.add_argument("-o", "--output", default="kb")
    p.add_argument("--auto", action="store_true", help="自动模式（跳过人工确认，测试用）")

    p = sub.add_parser("config", help="配置 LLM（交互式，写入 ~/.kbflow/config.ini）")

    p = sub.add_parser("scan", help="K01 事实扫描")
    p.add_argument("project", help="Java 项目路径")
    p.add_argument("-o", "--output", default="kb")

    p = sub.add_parser("divide", help="K02 领域划分")
    p.add_argument("-o", "--output", default="kb")

    p = sub.add_parser("confirm", help="K03 边界确认")
    p.add_argument("-o", "--output", default="kb")

    p = sub.add_parser("knowledge", help="K04 领域知识骨架")
    p.add_argument("domain")
    p.add_argument("service")
    p.add_argument("-o", "--output", default="kb")

    p = sub.add_parser("cross", help="K05 跨服务链路")
    p.add_argument("domain")
    p.add_argument("-o", "--output", default="kb")

    p = sub.add_parser("meta", help="K06 服务元信息")
    p.add_argument("service")
    p.add_argument("-o", "--output", default="kb")
    p = sub.add_parser("index", help="K07 全局导航")
    p.add_argument("-o", "--output", default="kb")

    p = sub.add_parser("narrate", help="K08 可读性交付")
    p.add_argument("domain")
    p.add_argument("service")
    p.add_argument("-o", "--output", default="kb")

    p = sub.add_parser("sync", help="框架→知识库同步")
    p.add_argument("kb_dir")
    p.add_argument("--strict", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.cmd is None:
            parser.print_help()
            return 0
        if args.cmd == "run":
            return _cmd_run(args)
        if args.cmd == "config":
            return _cmd_config(args)
        if args.cmd == "scan":
            return _cmd_scan(args)
        if args.cmd == "init":
            return _cmd_init(args)
        if args.cmd == "divide":
            return _cmd_divide(args)
        if args.cmd == "confirm":
            return _cmd_confirm(args)
        if args.cmd == "knowledge":
            return _cmd_knowledge(args)
        if args.cmd == "cross":
            return _cmd_cross(args)
        if args.cmd == "meta":
            return _cmd_meta(args)
        if args.cmd == "index":
            return _cmd_index(args)
        if args.cmd == "narrate":
            return _cmd_narrate(args)
        if args.cmd == "sync":
            return _cmd_sync(args)
        print("命令未接线: %s" % args.cmd)
        return 0
    except LLMError as e:
        print("\n❌ %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
