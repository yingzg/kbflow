from kbflow.stages.k02_divide import (
    _parse_domains,
    build_boundary_matrix,
    classify_entries,
    domains_to_toon,
    extract_feature_library,
    suggest_domains,
    toon_to_domains,
)


def test_build_boundary_matrix():
    domains = [
        {
            "name": "调拨",
            "responsibility": "调拨单生命周期",
            "key_entities": ["调拨单"],
            "boundary_included": ["申请", "审批"],
            "boundary_excluded": ["采购"],
        },
    ]
    matrix = build_boundary_matrix(domains)
    assert matrix[0]["id"] == "D1"
    assert matrix[0]["name"] == "调拨"
    assert matrix[0]["key_entities"] == "调拨单"
    assert matrix[0]["boundary_included"] == "申请|审批"
    assert matrix[0]["boundary_excluded"] == "采购"


def test_extract_feature_library():
    entries = [{"id": "API-001", "class_name": "TransferServiceImpl"}]
    domains = [{"name": "调拨"}]
    assignments = {"API-001": "调拨"}
    lib = extract_feature_library(entries, domains, assignments)
    assert lib[0]["sample_classes"] == "TransferServiceImpl"


def test_parse_domains():
    resp = '[{"name": "调拨", "key_entities": ["调拨单"]}]'
    domains = _parse_domains(resp)
    assert domains[0]["name"] == "调拨"


def test_suggest_domains_with_mock():
    class FakeLLM:
        def complete(self, prompt, system=""):
            return (
                '[{"name": "调拨", "responsibility": "x", "key_entities": ["调拨单"],'
                ' "boundary_included": ["审批"], "boundary_excluded": []}]'
            )

    signals = [
        {"id": "API-001", "class_name": "TransferServiceImpl", "package": "com.example",
         "doc": "调拨", "methods": "approve"}
    ]
    domains = suggest_domains(FakeLLM(), signals)
    assert domains[0]["name"] == "调拨"


def test_domains_toon_roundtrip():
    domains = [
        {"name": "调拨", "responsibility": "调拨单生命周期", "key_entities": ["调拨单"],
         "boundary_included": ["审批"], "boundary_excluded": []},
        {"name": "库存", "responsibility": "库存管理", "key_entities": ["库存记录"],
         "boundary_included": [], "boundary_excluded": ["作业执行"]},
    ]
    text = domains_to_toon(domains)
    assert "domains[2]" in text
    parsed = toon_to_domains(text)
    assert len(parsed) == 2
    assert parsed[0]["name"] == "调拨"
    assert parsed[0]["key_entities"] == ["调拨单"]
    assert parsed[1]["boundary_excluded"] == ["作业执行"]


def test_classify_entries():
    class FakeLLM:
        def complete(self, prompt, system=""):
            return (
                '[{"entry_id": "API-001", "domain": "调拨", "reason": "调拨服务:创建/审批→调拨"}]'
            )

    entries = [
        {"id": "API-001", "class_name": "TransferServiceImpl", "package": "com.example",
         "doc": "调拨", "methods": ""}
    ]
    domains = [{"name": "调拨", "responsibility": "调拨单生命周期"}]
    result = classify_entries(FakeLLM(), entries, domains)
    assert result[0]["domain"] == "调拨"
    assert result[0]["reason"]
