from kbflow.stages.k07_index import generate_panorama_md
from kbflow.stages.k08_narrate import seal_facts


def test_seal_facts():
    entries = [{"class_name": "TransferServiceImpl"}, {"class_name": "TransferController"}]
    tables = [{"name": "transfer_order"}]
    facts = seal_facts("调拨", "transfer-service", entries, tables)
    assert facts["entry_count"] == 2
    assert facts["table_count"] == 1
    assert facts["entries"] == ["TransferServiceImpl", "TransferController"]


def test_generate_panorama_md():
    matrix = [
        {"id": "D1", "name": "调拨", "responsibility": "调拨流转", "key_entities": "调拨单"},
        {"id": "D2", "name": "库存", "responsibility": "库存管理", "key_entities": "库存"},
    ]
    pano = generate_panorama_md(matrix, "svc")
    assert "领域依赖矩阵" in pano
    assert "调拨" in pano
    assert "库存" in pano
    assert "From \\ To" in pano
