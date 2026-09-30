from kbflow.stages.k04_knowledge import PLACEHOLDER
from kbflow.stages.k05_cross import (
    build_cross_service_links,
    build_domain_overview,
    enrich_domain_overview,
)


def test_domain_overview_with_business_processes():
    entries = [
        {"id": "API-001", "class_name": "BocAppProviderImpl", "kind": "dubbo",
         "doc": "活动政策管理", "methods": ""},
        {"id": "API-002", "class_name": "IntlPolicyBpmProviderImpl", "kind": "dubbo",
         "doc": "", "methods": ""},
    ]
    overview = build_domain_overview("政策管理", "transfer-service", entries)
    assert overview["domain"] == "政策管理"
    assert overview["services"][0]["name"] == "transfer-service"
    assert len(overview["business_processes"]) == 2
    assert overview["business_processes"][0]["entry_api"] == "BocAppProviderImpl"
    assert overview["business_processes"][0]["name"] == "活动政策管理"


def test_cross_service_links_maps_node_id_to_class():
    entries = [
        {"id": "API-001", "class_name": "BocAppProviderImpl", "kind": "dubbo", "doc": "", "methods": ""},
    ]
    topology = {
        "nodes": {
            "entries": [{"id": "N1", "class": "BocAppProviderImpl", "type": "dubbo_provider"}],
            "services": [],
            "external": [{"id": "E1", "class": "AccountProvider"}],
        },
        "edges": {
            "internal": [],
            "external": [{"from": "N1", "to": "E1", "kind": "dubbo_reference"}],
        },
    }
    links = build_cross_service_links(entries, topology, "transfer-service")
    assert links["api_entries"]["dubbo"][0]["class"] == "BocAppProviderImpl"
    assert links["external_system_dependencies_summary"][0]["systems"] == "AccountProvider"


def test_enrich_domain_overview():
    class FakeLLM:
        def complete(self, prompt, system=""):
            return '{"description": "面向渠道激励与活动政策管理", "scope": "包含政策配置与审批，不含对账结算"}'

    entries = [{"id": "API-001", "class_name": "BocAppProviderImpl", "kind": "dubbo", "doc": "", "methods": ""}]
    overview = build_domain_overview("政策管理", "transfer-service", entries)
    overview = enrich_domain_overview(FakeLLM(), "政策管理", overview, entries)
    assert overview["description"] == "面向渠道激励与活动政策管理"
    assert overview["scope"] == "包含政策配置与审批，不含对账结算"
