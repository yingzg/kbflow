from kbflow.stages.k04_knowledge import PLACEHOLDER


def build_service_meta(service_name, entries, matrix, mapping):
    stats = {"dubbo": 0, "rest": 0, "mq": 0, "job": 0}
    for e in entries:
        kind = e.get("kind", "")
        if kind in stats:
            stats[kind] += 1

    domain_count = {}
    for m in mapping:
        domain_count[m["domain_ref"]] = domain_count.get(m["domain_ref"], 0) + 1
    ref_to_name = {d["id"]: d["name"] for d in matrix}
    domain_coverage = [
        {"domain": ref_to_name.get(ref, ref), "entry_count": count}
        for ref, count in domain_count.items()
    ]

    modules = _extract_modules(entries)

    return {
        "identity": {
            "name": service_name,
            "description": PLACEHOLDER,
            "core_responsibilities": PLACEHOLDER,
        },
        "domain_coverage": domain_coverage,
        "modules": modules,
        "entry_stats": {
            "dubbo_api": stats["dubbo"],
            "rest_api": stats["rest"],
            "mq_consumer": stats["mq"],
            "scheduled_job": stats["job"],
            "total": len(entries),
        },
    }


def _extract_modules(entries):
    from collections import Counter

    counter = Counter()
    class_by_module = {}
    for e in entries:
        parts = [p for p in e.get("package", "").split(".") if p]
        module = ".".join(parts[-2:]) if len(parts) >= 2 else e.get("package", "")
        counter[module] += 1
        class_by_module.setdefault(module, []).append(e["class_name"])
    return [
        {
            "name": module,
            "entry_count": counter[module],
            "key_classes": "|".join(class_by_module[module][:3]),
        }
        for module, _ in counter.most_common()
    ]


def build_tech_config(mavens):
    return {
        "tech_stack": [
            {"name": aid, "version": coord}
            for aid, coord in mavens.items()
        ]
    }


def build_dev_standards(entries):
    naming = []
    patterns = (
        ("Controller", "*Controller", "HTTP接口控制器"),
        ("ProviderImpl", "*ProviderImpl", "Dubbo接口实现"),
        ("Consumer", "*Consumer", "消息消费处理"),
        ("Task", "*Task", "定时任务处理"),
        ("ServiceImpl", "*ServiceImpl", "领域服务实现"),
        ("RepositoryImpl", "*RepositoryImpl", "数据访问实现"),
        ("Mapper", "*Mapper", "数据库Mapper接口"),
    )
    for suffix, pattern, desc in patterns:
        example = next((e["class_name"] for e in entries if e["class_name"].endswith(suffix)), "")
        if example:
            naming.append({
                "type": suffix,
                "pattern": pattern,
                "example": example,
                "description": desc,
            })

    documented = [e for e in entries if e.get("doc")]
    documented.sort(key=lambda e: len(e.get("doc", "")), reverse=True)
    example_classes = [
        {
            "class_name": e["class_name"],
            "role": _infer_role(e["class_name"]),
            "why": e.get("doc", "")[:50],
        }
        for e in documented[:5]
    ]

    return {
        "naming_conventions": naming,
        "example_classes": example_classes,
    }


def _infer_role(class_name):
    for suffix, role in (
        ("Controller", "HTTP入口"),
        ("ProviderImpl", "Dubbo入口"),
        ("Consumer", "MQ消费者"),
        ("Task", "定时任务"),
        ("ServiceImpl", "领域服务"),
        ("Mapper", "数据访问"),
    ):
        if class_name.endswith(suffix):
            return role
    return "业务服务"
