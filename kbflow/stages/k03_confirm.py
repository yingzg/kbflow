import json
import re
from concurrent.futures import ThreadPoolExecutor

from kbflow.toon import toon_dumps, toon_loads

_SCORE_SYSTEM = (
    "你是领域划分评审专家。你对一个业务入口是否归属某个领域做四维评分，"
    "返回 JSON：{\"score\": 0-100 整数, \"decision\": \"KEEP|MOVE|DELETE\", "
    "\"target_domain\": 领域名或空, \"reason\": 一句话理由}。"
    "四维权重：类名语义 35 / 注释+方法 25 / 包路径 20 / 边界对比 20。"
    "score < 70 说明归属不明确，需要人工复核。"
)


def classify_by_score(score, threshold=70):
    return "accept" if score >= threshold else "review"


def score_entry(llm, entry, domains):
    prompt = (
        "业务入口：类名=%s，包=%s，注释=%s，方法=%s\n"
        "候选领域边界矩阵：\n%s\n"
        "请判断该入口最可能属于哪个领域，并给出四维评分。只输出 JSON。"
        % (
            entry["class_name"], entry["package"], entry.get("doc", ""), entry.get("methods", ""),
            json.dumps(domains, ensure_ascii=False),
        )
    )
    resp = llm.complete(prompt, system=_SCORE_SYSTEM)
    return _parse_score(resp)


def _parse_score(resp):
    m = re.search(r"\{.*\}", resp, re.DOTALL)
    if not m:
        return {"score": 0, "decision": "KEEP", "target_domain": "", "reason": "无法解析"}
    return json.loads(m.group(0))


def _parse_scores(resp):
    m = re.search(r"\[.*\]", resp, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return []


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


def _build_batch_prompt(batch, domains):
    lines = [
        "%s | %s | %s | %s | %s" % (
            e["id"], e["class_name"], e["package"], _truncate(e.get("doc", ""), 60),
            _method_names(e.get("methods", "")),
        )
        for e in batch
    ]
    return (
        "以下是 %d 个业务入口和领域边界矩阵。\n"
        "请对每个入口做四维评分（类名语义35 / 注释25 / 包路径20 / 边界对比20），"
        "返回 JSON 数组，每个元素格式：\n"
        '{"entry_id": 入口ID, "score": 0-100整数, "decision": "KEEP|MOVE|DELETE", "target_domain": 领域名或空, "reason": 一句话理由}\n\n'
        "入口清单（每行：入口ID | 类名 | 包路径 | 注释 | 方法名）：\n%s\n\n"
        "领域边界矩阵：\n%s\n\n"
        "只输出 JSON 数组，不要多余文字。"
        % (len(batch), "\n".join(lines), json.dumps(domains, ensure_ascii=False))
    )


def score_entries_batch(llm, entries, domains, batch_size=25, progress=None, max_workers=4):
    batches = [entries[i:i + batch_size] for i in range(0, len(entries), batch_size)]
    total = len(batches)

    def _score(batch, batch_no):
        if progress and (max_workers == 1 or total == 1):
            progress(batch_no, total, len(batch))
        resp = llm.complete(_build_batch_prompt(batch, domains), system=_SCORE_SYSTEM)
        return _parse_scores(resp)

    if max_workers > 1 and total > 1:
        workers = min(max_workers, total)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(
                lambda pair: _score(*pair),
                [(b, i + 1) for i, b in enumerate(batches)],
            ))
    else:
        results = [_score(b, i + 1) for i, b in enumerate(batches)]

    reviews = []
    for r in results:
        reviews.extend(r)
    return reviews


def reviews_to_toon(reviews):
    rows = []
    for r in reviews:
        rows.append({
            "entry_id": r["entry_id"],
            "class_name": r["class_name"],
            "score": r.get("score", 0),
            "suggested": r.get("suggested", "KEEP"),
            "target_domain": r.get("target_domain", ""),
            "decision": r.get("decision", ""),
            "reason": r.get("reason", ""),
        })
    return toon_dumps({"reviews": rows})


def toon_to_reviews(text):
    doc = toon_loads(text)
    reviews = []
    for r in doc.get("reviews", []):
        reviews.append({
            "entry_id": r["entry_id"],
            "class_name": r["class_name"],
            "score": r.get("score", 0),
            "suggested": r.get("suggested", "KEEP"),
            "target_domain": r.get("target_domain", ""),
            "decision": r.get("decision", ""),
            "reason": r.get("reason", ""),
        })
    return reviews


def reviews_to_markdown(reviews):
    lines = ["# K03 低置信度复核清单", ""]
    lines.append("每条填写「最终决定」，改完保存后回到终端按 Enter 继续。留空 = 采纳建议。")
    lines.append("可选值：KEEP / MOVE / MOVE:领域名 / DELETE")
    lines.append("")
    for i, r in enumerate(reviews, 1):
        suggested = r.get("suggested", "KEEP")
        target = r.get("target_domain", "")
        move_desc = " → " + target if suggested == "MOVE" and target else ""
        lines.append("### %d. %s - %s" % (i, r["entry_id"], r["class_name"]))
        lines.append("")
        lines.append("- 建议：%s%s" % (suggested, move_desc))
        lines.append("- 总分：%s / 100" % r.get("score", 0))
        if r.get("reason"):
            lines.append("- 理由：%s" % r["reason"])
        lines.append("")
        lines.append("可选决定：")
        lines.append("- KEEP —— 保持现状")
        if suggested == "MOVE" and target:
            lines.append("- MOVE —— 移动到建议领域（%s）" % target)
        else:
            lines.append("- MOVE:领域名 —— 移动到指定领域")
        lines.append("- DELETE —— 删除（归入未分类 D99）")
        lines.append("")
        lines.append("**最终决定**：")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def markdown_to_reviews(text):
    sections = re.split(r"### (\d+)\. ([\w-]+) - ([^\n]+)", text)
    reviews = []
    i = 1
    while i + 2 < len(sections):
        entry_id = sections[i + 1]
        class_name = sections[i + 2]
        body = sections[i + 3] if i + 3 < len(sections) else ""
        suggested = "KEEP"
        target = ""
        score = 0
        m = re.search(r"- 建议：(\w+)(?: → (.+))?", body)
        if m:
            suggested = m.group(1)
            target = (m.group(2) or "").strip()
        m = re.search(r"- 总分：(\d+) / 100", body)
        if m:
            score = int(m.group(1))
        decision = ""
        m = re.search(r"\*\*最终决定\*\*：\s*([^\n]*)", body)
        if m:
            user = m.group(1).strip()
            user = re.sub(r"[（(].*?[)）]", "", user).strip()
            if user:
                decision = user
        reviews.append({
            "entry_id": entry_id,
            "class_name": class_name,
            "score": score,
            "suggested": suggested,
            "target_domain": target,
            "decision": decision,
            "reason": "",
        })
        i += 4
    return reviews


def apply_decision(review):
    raw = review.get("decision", "").strip()
    if raw.startswith("MOVE:") and len(raw) > 5:
        decision, domain = "MOVE", raw[5:].strip()
    elif raw in ("KEEP", "MOVE", "DELETE"):
        decision = raw
        domain = "D99" if raw == "DELETE" else review.get("target_domain", "")
    else:
        decision = review.get("suggested", "KEEP")
        domain = "D99" if decision == "DELETE" else review.get("target_domain", "")
    return {
        "entry_id": review["entry_id"],
        "class_name": review["class_name"],
        "domain": domain,
        "decision": decision,
    }
