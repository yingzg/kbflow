import re

from kbflow.toon import toon_dumps, toon_loads


def classify_by_score(score, threshold=70):
    return "accept" if score >= threshold else "review"


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
