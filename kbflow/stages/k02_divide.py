import json
import re

from kbflow.toon import toon_dumps, toon_loads

_DOMAIN_SUGGESTION_SYSTEM = (
    "你是资深领域驱动设计（DDD）专家。你根据代码事实清单，把 Java 微服务里的业务入口"
    "聚类成业务领域（限界上下文）。领域是「一组内聚的业务能力，有明确边界」。\n"
    "关键约束：\n"
    "1. 领域是「限界上下文」级别，通常 5-8 个，不要切成过细的功能模块。\n"
    "2. 技术性通用能力（枚举、字典、文件上传下载、日志、测试、权限）归入「公共支撑」领域。\n"
    "3. 纯查询/工作台/汇总统计类入口，归入其所属业务域，不要单独成领域。"
)


_CLASSIFY_SYSTEM = (
    "你是领域分类专家。你把业务入口分类到给定的领域清单中。"
    "返回 JSON 数组，每个元素：{\"entry_id\": 入口ID, \"domain\": 领域名, \"reason\": \"类名:业务动作→领域\"}。"
    "无法确定归属的，domain 填 \"unclassified\"。宁可拒识，不要误识。"
)


def domains_to_toon(domains):
    rows = []
    for d in domains:
        rows.append({
            "name": d.get("name", ""),
            "responsibility": d.get("responsibility", ""),
            "key_entities": "|".join(d.get("key_entities", [])),
            "boundary_included": "|".join(d.get("boundary_included", [])),
            "boundary_excluded": "|".join(d.get("boundary_excluded", [])),
        })
    return toon_dumps({"domains": rows})


def toon_to_domains(text):
    doc = toon_loads(text)
    domains = []
    for r in doc.get("domains", []):
        domains.append({
            "name": r.get("name", ""),
            "responsibility": r.get("responsibility", ""),
            "key_entities": _split_pipe(r.get("key_entities", "")),
            "boundary_included": _split_pipe(r.get("boundary_included", "")),
            "boundary_excluded": _split_pipe(r.get("boundary_excluded", "")),
        })
    return domains


def _split_pipe(s):
    return [x for x in s.split("|") if x] if s else []


def load_entries(meta_dir):
    text = (meta_dir / "behavior.toon").read_text(encoding="utf-8")
    doc = toon_loads(text)
    entries = []
    for kind in ("dubbo", "rest", "mq", "job"):
        for bucket in ("with_doc", "no_doc"):
            for e in doc.get(kind, {}).get(bucket, []):
                entries.append({
                    "id": e["id"],
                    "class_name": e["class_name"],
                    "package": e.get("package", ""),
                    "doc": e.get("doc", ""),
                    "methods": e.get("methods", ""),
                    "kind": kind,
                    "has_doc": bucket == "with_doc",
                })
    return entries


def extract_signals(entries):
    return [
        {
            "id": e["id"],
            "class_name": e["class_name"],
            "package": e["package"],
            "doc": e["doc"],
            "methods": e["methods"],
        }
        for e in entries
    ]


def suggest_domains(llm, signals):
    prompt = (
        "以下是代码库的业务入口清单（每行：入口ID | 类名 | 包路径 | 注释 | 方法）。\n"
        "请把它们聚类成业务领域，返回 JSON 数组，每个元素格式：\n"
        '{"name": 领域名, "responsibility": 一句话职责, '
        '"key_entities": [核心实体名], "boundary_included": [包含的能力词], '
        '"boundary_excluded": [排除的能力词]}\n\n'
    )
    for s in signals:
        prompt += "%s | %s | %s | %s | %s\n" % (
            s["id"], s["class_name"], s["package"], s["doc"], s["methods"],
        )
    prompt += "\n只输出 JSON 数组，不要多余文字。"
    resp = llm.complete(prompt, system=_DOMAIN_SUGGESTION_SYSTEM)
    return _parse_domains(resp)


def _parse_domains(resp):
    m = re.search(r"\[.*\]", resp, re.DOTALL)
    if not m:
        return []
    return json.loads(m.group(0))


def _truncate(s, n):
    return s if len(s) <= n else s[:n] + "…"


def _method_names(methods_str, limit=12):
    names = []
    for part in methods_str.split(";"):
        part = part.strip()
        if not part:
            continue
        name = part.split("(")[0].strip()
        if name and name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return "|".join(names)


def _parse_classifications(resp):
    m = re.search(r"\[.*\]", resp, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return []


def classify_entries(llm, entries, domains, batch_size=25, progress=None):
    domain_names = [d["name"] for d in domains]
    domain_desc = "\n".join(
        "%s: %s" % (d["name"], d.get("responsibility", ""))
        for d in domains
    )
    entry_class = {e["id"]: e["class_name"] for e in entries}

    ordered = sorted(entries, key=lambda e: 0 if e.get("doc") else 1)

    feature_library = {}
    classifications = []
    batches = [ordered[i:i + batch_size] for i in range(0, len(ordered), batch_size)]
    total = len(batches)
    for i, batch in enumerate(batches):
        if progress:
            progress(i + 1, total, len(batch))
        lines = [
            "%s | %s | %s | %s | %s" % (
                e["id"], e["class_name"], e["package"], _truncate(e.get("doc", ""), 60),
                _method_names(e.get("methods", "")),
            )
            for e in batch
        ]
        feature_text = ""
        if feature_library:
            feature_text = "\n\n已知领域特征（参考分类）：\n" + "\n".join(
                "%s: %s" % (d, ";".join(sorted(cs)))
                for d, cs in feature_library.items()
            )
        prompt = (
            "领域清单：\n%s\n\n"
            "以下是 %d 个业务入口（每行：入口ID | 类名 | 包路径 | 注释 | 方法名）。\n"
            "请把每个入口分类到最合适的领域，返回 JSON 数组，每个元素：\n"
            '{"entry_id": 入口ID, "domain": 领域名, "reason": "类名:业务动作→领域"}\n'
            "%s\n\n"
            "入口清单：\n%s\n\n只输出 JSON 数组，不要多余文字。"
            % (domain_desc, len(batch), feature_text, "\n".join(lines))
        )
        resp = llm.complete(prompt, system=_CLASSIFY_SYSTEM)
        batch_result = _parse_classifications(resp)
        for c in batch_result:
            domain = c.get("domain", "")
            if domain in domain_names:
                cls = entry_class.get(c.get("entry_id", ""))
                if cls:
                    feature_library.setdefault(domain, set()).add(cls)
        classifications.extend(batch_result)
    return classifications


def build_boundary_matrix(domains):
    matrix = []
    for i, d in enumerate(domains, 1):
        matrix.append({
            "id": "D%d" % i,
            "name": d["name"],
            "responsibility": d.get("responsibility", ""),
            "key_entities": ",".join(d.get("key_entities", [])),
            "boundary_included": "|".join(d.get("boundary_included", [])),
            "boundary_excluded": "|".join(d.get("boundary_excluded", [])),
        })
    return matrix


def extract_feature_library(entries, domains, assignments):
    library = {d["name"]: [] for d in domains}
    for e in entries:
        domain_name = assignments.get(e["id"])
        if domain_name in library:
            library[domain_name].append(e["class_name"])
    return [
        {"domain": name, "sample_classes": ";".join(classes)}
        for name, classes in library.items()
    ]
