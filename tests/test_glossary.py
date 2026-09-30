from kbflow.glossary.extract import extract_candidates, strip_suffix
from kbflow.glossary.merge import merge_glossary


def test_strip_suffix():
    assert strip_suffix("TransferServiceImpl") == "Transfer"
    assert strip_suffix("TransferOrder") == "TransferOrder"
    assert strip_suffix("StockRecord") == "StockRecord"


def test_extract_candidates():
    entries = [{"class_name": "TransferServiceImpl", "package": "com.example.wms.transfer"}]
    candidates = extract_candidates(entries)
    assert candidates[0]["name"] == "Transfer"
    assert candidates[0]["scope"] == "transfer"
    assert candidates[0]["code"] == "TransferServiceImpl"


def test_merge_does_not_override_verified():
    existing = [{"name": "Transfer", "zh": "调拨（人工确认）", "status": "verified"}]
    candidates = [{"name": "Transfer", "zh": "调拨（自动）", "status": "draft"}]
    merged = merge_glossary(existing, candidates)
    assert merged[0]["zh"] == "调拨（人工确认）"


def test_merge_adds_new():
    existing = [{"name": "A", "zh": "x", "status": "verified"}]
    candidates = [{"name": "B", "zh": "y", "status": "draft"}]
    merged = merge_glossary(existing, candidates)
    assert len(merged) == 2
