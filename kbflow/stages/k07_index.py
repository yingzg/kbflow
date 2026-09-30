def generate_panorama_md(matrix, service_name):
    names = [d["name"] for d in matrix]
    lines = ["# 领域依赖全景图", ""]
    lines.append("## 1. 领域清单")
    for d in matrix:
        lines.append("- %s %s：%s。核心聚合：%s。服务：`%s`" % (
            d["id"], d["name"], d.get("responsibility", ""), d.get("key_entities", ""), service_name,
        ))
    lines.append("")
    lines.append("## 2. 领域依赖矩阵")
    lines.append("> 标记：D=数据依赖，E=事件依赖，F=流程依赖")
    lines.append("")
    lines.append("| From \\ To | " + " | ".join(names) + " |")
    lines.append("| --- | " + " | ".join(["---"] * len(names)) + " |")
    for d in matrix:
        lines.append("| %s | " % d["name"] + " | ".join(["—"] * len(names)) + " |")
    lines.append("")
    lines.append("## 3. 双向依赖视图")
    for d in matrix:
        lines.append("- %s 上游：无已识别依赖。下游：无已识别影响。" % d["name"])
    return "\n".join(lines)
