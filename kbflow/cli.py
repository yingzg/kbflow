import argparse
import sys
from pathlib import Path

from kbflow.llm import LLMError
from kbflow.stages.k01_scan import ScanError, run_scan
from kbflow.sync.sync_kb import sync_to_kb
from kbflow.toon import toon_dumps
from kbflow import tools


def _cmd_config(args):
    import configparser

    cfg_dir = Path.home() / ".kbflow"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "config.ini"

    print("\nKBFlow 配置向导\n")

    print("【1/2】数据库配置（可选，K01 读真实表结构用；直接回车跳过）")
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
    if mcp_command:
        parser["database"] = db_section
        parser["database.env"] = db_env
    with open(cfg_path, "w", encoding="utf-8") as f:
        parser.write(f)
    print("\n✅ 配置已写入 %s" % cfg_path)
    print("  语义由 AI IDE 完成，KBFlow 只做事实处理。")
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
    parser = argparse.ArgumentParser(
        prog="kbflow", description="代码知识库构建工具（AI IDE 驱动，脚本做事实、AI 做语义）"
    )
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("init", help="初始化知识库目录")
    p.add_argument("kb_dir", nargs="?", default="kb")

    p = sub.add_parser("config", help="配置数据库连接（可选，写入 ~/.kbflow/config.ini）")

    p = sub.add_parser("scan", help="K01 事实扫描")
    p.add_argument("project", help="Java 项目路径")
    p.add_argument("-o", "--output", default="kb")

    p = sub.add_parser("sync", help="框架→知识库同步")
    p.add_argument("kb_dir")
    p.add_argument("--strict", action="store_true")

    p = sub.add_parser("json2toon", help="AI 输出 json → 转 toon 落盘（写路径）")
    p.add_argument("--json-file", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--wrap", help="把数据包进这个 key（如 reviews）")

    p = sub.add_parser("matrix", help="K02 领域建议 → 边界矩阵")
    p.add_argument("--domains", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("checklist", help="K03 复核清单生成/解析")
    p.add_argument("action", choices=["gen", "parse"])
    p.add_argument("--reviews", help="评分结果 toon（gen 用）")
    p.add_argument("--checklist", help="复核清单 md（parse 用）")
    p.add_argument("--out", required=True)
    p.add_argument("--threshold", type=int, default=70)

    p = sub.add_parser("skeleton", help="K04/K05/K06 骨架生成（带 [待AI补充] 占位）")
    p.add_argument("kind", help="overview/interface/data-model/domain-overview/cross-links/service-meta/tech-config/dev-standards")
    p.add_argument("--domain", required=True)
    p.add_argument("--service", required=True)
    p.add_argument("-o", "--output", default="kb")

    p = sub.add_parser("seal", help="K08 事实密封（确定性部分）")
    p.add_argument("--domain", required=True)
    p.add_argument("--service", required=True)
    p.add_argument("-o", "--output", default="kb")
    p.add_argument("--out", help="输出 toon 路径（缺省打印 json）")

    p = sub.add_parser("panorama", help="K07 全景图（确定性部分）")
    p.add_argument("--matrix", required=True)
    p.add_argument("--service", required=True)
    p.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    try:
        if args.cmd is None:
            parser.print_help()
            return 0
        if args.cmd == "init":
            return _cmd_init(args)
        if args.cmd == "config":
            return _cmd_config(args)
        if args.cmd == "scan":
            return _cmd_scan(args)
        if args.cmd == "sync":
            return _cmd_sync(args)
        if args.cmd == "json2toon":
            return tools.cmd_json2toon(args)
        if args.cmd == "matrix":
            return tools.cmd_matrix(args)
        if args.cmd == "checklist":
            if args.action == "gen":
                return tools.cmd_checklist_gen(args)
            return tools.cmd_checklist_parse(args)
        if args.cmd == "skeleton":
            return tools.cmd_skeleton(args)
        if args.cmd == "seal":
            return tools.cmd_seal(args)
        if args.cmd == "panorama":
            return tools.cmd_panorama(args)
        print("命令未接线: %s" % args.cmd)
        return 0
    except LLMError as e:
        print("\n❌ %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
