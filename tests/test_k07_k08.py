from kbflow.stages.k07_index import generate_panorama_md
from kbflow.stages.k08_narrate import generate_glossary, narrate, seal_facts


def test_seal_facts():
    entries = [{"class_name": "TransferServiceImpl"}, {"class_name": "TransferController"}]
    tables = [{"name": "transfer_order"}]
    facts = seal_facts("调拨", "transfer-service", entries, tables)
    assert facts["entry_count"] == 2
    assert facts["table_count"] == 1
    assert facts["entries"] == ["TransferServiceImpl", "TransferController"]


def test_narrate_with_mock():
    class FakeLLM:
        def complete(self, prompt, system=""):
            return "该服务负责调拨单的全生命周期。"

    facts = {"service": "transfer-service", "domain": "调拨", "entry_count": 2,
             "table_count": 1, "entries": ["A", "B"], "tables": ["t1"]}
    narrative = narrate(FakeLLM(), facts)
    assert "调拨单" in narrative


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


def test_generate_glossary_batch():
    class FakeLLM:
        def __init__(self):
            self.calls = 0

        def complete(self, prompt, system=""):
            self.calls += 1
            return '[{"name": "Transfer", "zh": "调拨"}, {"name": "Stock", "zh": "库存"}]'

    entries = [
        {"class_name": "TransferServiceImpl", "package": "com.acme.transfer"},
        {"class_name": "StockServiceImpl", "package": "com.acme.stock"},
    ]
    llm = FakeLLM()
    glossary = generate_glossary(llm, entries)
    assert llm.calls == 1
    names = {g["name"]: g["zh"] for g in glossary}
    assert names["Transfer"] == "调拨"
    assert names["Stock"] == "库存"
