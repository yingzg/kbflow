from kbflow.stages.k06_meta import (
    build_dev_standards,
    build_service_meta,
    build_tech_config,
    enrich_service_meta,
)


def test_build_service_meta():
    entries = [
        {"id": "API-001", "class_name": "BocAppProviderImpl", "kind": "dubbo",
         "package": "com.acme.app.provider", "doc": "", "methods": ""},
        {"id": "API-002", "class_name": "BocController", "kind": "rest",
         "package": "com.acme.app.controller", "doc": "", "methods": ""},
    ]
    matrix = [{"id": "D1", "name": "政策管理"}]
    mapping = [{"entry_id": "API-001", "domain_ref": "D1"},
               {"entry_id": "API-002", "domain_ref": "D1"}]
    meta = build_service_meta("svc", entries, matrix, mapping)
    assert meta["identity"]["name"] == "svc"
    assert meta["entry_stats"]["dubbo_api"] == 1
    assert meta["entry_stats"]["rest_api"] == 1
    assert meta["domain_coverage"][0]["domain"] == "政策管理"
    assert meta["domain_coverage"][0]["entry_count"] == 2


def test_build_tech_config():
    tech = build_tech_config({"stock-api": "com.example:stock-api (1.0.0)"})
    assert tech["tech_stack"][0]["name"] == "stock-api"


def test_build_dev_standards():
    entries = [
        {"class_name": "BocController", "kind": "rest", "package": "com.acme", "doc": "政策控制器"},
        {"class_name": "BocAppProviderImpl", "kind": "dubbo", "package": "com.acme", "doc": "政策应用"},
        {"class_name": "PolicySyncTask", "kind": "job", "package": "com.acme", "doc": ""},
    ]
    standards = build_dev_standards(entries)
    patterns = [n["pattern"] for n in standards["naming_conventions"]]
    assert "*Controller" in patterns
    assert "*ProviderImpl" in patterns
    assert "*Task" in patterns
    assert standards["example_classes"][0]["role"] == "HTTP入口"


def test_enrich_service_meta():
    class FakeLLM:
        def complete(self, prompt, system=""):
            return '{"description": "面向国际返佣业务的服务", "core_responsibilities": ["政策管理", "预算管理"]}'

    meta = {
        "identity": {"name": "svc", "description": "[待AI补充]", "core_responsibilities": "[待AI补充]"},
        "domain_coverage": [{"domain": "政策管理", "entry_count": 17}],
    }
    meta = enrich_service_meta(FakeLLM(), "svc", meta)
    assert meta["identity"]["description"] == "面向国际返佣业务的服务"
    assert meta["identity"]["core_responsibilities"] == ["政策管理", "预算管理"]
