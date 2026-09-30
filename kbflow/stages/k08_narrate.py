import json
import re

from kbflow.glossary.extract import extract_candidates
from kbflow.glossary.merge import merge_glossary

_NARRATE_SYSTEM = (
    "你是知识库文档写作者。你基于给定的结构化事实写自然语言叙述，"
    "让读者一眼看懂该服务在领域里做什么。禁止改动任何数字、清单或引用——只补充叙述。"
)

_GLOSSARY_SYSTEM = "你是领域业务分析师，用简洁中文解释业务名词（说清楚它是什么，不是做什么）。"


def seal_facts(domain, service, entries, tables):
    return {
        "service": service,
        "domain": domain,
        "entry_count": len(entries),
        "entries": [e["class_name"] for e in entries],
        "table_count": len(tables),
        "tables": [t["name"] for t in tables],
    }


def generate_glossary(llm, entries, existing=None, key_entities=None):
    candidates = extract_candidates(entries, key_entities)
    names = [c["name"] for c in candidates]
    if not names:
        return merge_glossary(existing or [], candidates)
    prompt = (
        "以下是 %d 个业务名词。请给出每个名词的中文解释（一句话，说清楚它是什么，不是做什么）。\n"
        "返回 JSON 数组，每个元素：{\"name\": 名词, \"zh\": 中文解释}\n\n"
        "名词列表：%s\n\n只输出 JSON 数组。"
        % (len(names), "|".join(names))
    )
    resp = llm.complete(prompt, system=_GLOSSARY_SYSTEM)
    m = re.search(r"\[.*\]", resp, re.DOTALL)
    zh_map = {}
    if m:
        try:
            for item in json.loads(m.group(0)):
                zh_map[item.get("name", "")] = item.get("zh", "")
        except (json.JSONDecodeError, TypeError):
            pass
    for c in candidates:
        c["zh"] = zh_map.get(c["name"], c["name"])
    return merge_glossary(existing or [], candidates)


def narrate(llm, facts):
    prompt = (
        "服务「%s」属于领域「%s」，共有 %d 个业务入口、%d 张数据表。\n"
        "入口清单：%s\n数据表清单：%s\n\n"
        "请写两段自然语言叙述：一句话定位 + 一段服务概述（这个服务负责什么、核心链路是什么）。"
        "只输出叙述文字，不要改动上面的事实清单。"
        % (
            facts["service"], facts["domain"], facts["entry_count"], facts["table_count"],
            ";".join(facts["entries"]), ";".join(facts["tables"]),
        )
    )
    return llm.complete(prompt, system=_NARRATE_SYSTEM)
