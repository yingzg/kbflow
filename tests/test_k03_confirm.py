from kbflow.stages.k03_confirm import (
    apply_decision,
    classify_by_score,
    markdown_to_reviews,
    reviews_to_markdown,
    reviews_to_toon,
    score_entries_batch,
    score_entry,
    toon_to_reviews,
)


def test_classify_by_score():
    assert classify_by_score(80) == "accept"
    assert classify_by_score(50) == "review"


def test_apply_decision_keep():
    r = apply_decision({
        "entry_id": "API-001", "class_name": "X",
        "suggested": "KEEP", "target_domain": "D1", "decision": "",
    })
    assert r["domain"] == "D1"
    assert r["decision"] == "KEEP"


def test_apply_decision_move():
    r = apply_decision({
        "entry_id": "API-001", "class_name": "X",
        "suggested": "KEEP", "target_domain": "D3", "decision": "MOVE",
    })
    assert r["domain"] == "D3"
    assert r["decision"] == "MOVE"


def test_apply_decision_delete():
    r = apply_decision({
        "entry_id": "API-001", "class_name": "X",
        "suggested": "KEEP", "target_domain": "", "decision": "DELETE",
    })
    assert r["domain"] == "D99"
    assert r["decision"] == "DELETE"


def test_apply_decision_default_to_suggested():
    r = apply_decision({
        "entry_id": "API-001", "class_name": "X",
        "suggested": "MOVE", "target_domain": "D3", "decision": "",
    })
    assert r["decision"] == "MOVE"
    assert r["domain"] == "D3"


def test_reviews_toon_roundtrip():
    reviews = [
        {"entry_id": "API-010", "class_name": "XxxImpl", "score": 45,
         "suggested": "MOVE", "target_domain": "调拨", "decision": "", "reason": "包路径"},
    ]
    text = reviews_to_toon(reviews)
    parsed = toon_to_reviews(text)
    assert parsed[0]["entry_id"] == "API-010"
    assert parsed[0]["suggested"] == "MOVE"
    assert parsed[0]["decision"] == ""


def test_reviews_markdown_roundtrip():
    reviews = [
        {"entry_id": "API-010", "class_name": "XxxImpl", "score": 45,
         "suggested": "MOVE", "target_domain": "调拨", "decision": "", "reason": "包路径指向调拨"},
        {"entry_id": "API-011", "class_name": "YyyImpl", "score": 30,
         "suggested": "DELETE", "target_domain": "", "decision": "", "reason": "测试类"},
    ]
    text = reviews_to_markdown(reviews)
    assert "API-010" in text
    assert "最终决定" in text
    parsed = markdown_to_reviews(text)
    assert len(parsed) == 2
    assert parsed[0]["entry_id"] == "API-010"
    assert parsed[0]["suggested"] == "MOVE"
    assert parsed[0]["target_domain"] == "调拨"


def test_apply_decision_move_to_named_domain():
    r = apply_decision({
        "entry_id": "API-001", "class_name": "X",
        "suggested": "KEEP", "target_domain": "D1", "decision": "MOVE:库存",
    })
    assert r["decision"] == "MOVE"
    assert r["domain"] == "库存"


def test_score_entries_batch_one_call_multiple_entries():
    class FakeLLM:
        def __init__(self):
            self.calls = 0

        def complete(self, prompt, system=""):
            self.calls += 1
            return (
                '[{"entry_id": "API-001", "score": 85, "decision": "KEEP", "target_domain": "调拨", "reason": ""},'
                ' {"entry_id": "API-002", "score": 45, "decision": "MOVE", "target_domain": "库存", "reason": ""}]'
            )

    llm = FakeLLM()
    entries = [
        {"id": "API-001", "class_name": "A", "package": "com.a", "doc": "", "methods": ""},
        {"id": "API-002", "class_name": "B", "package": "com.b", "doc": "", "methods": ""},
    ]
    reviews = score_entries_batch(llm, entries, [{"name": "调拨"}], batch_size=25)
    assert llm.calls == 1
    assert len(reviews) == 2
    assert reviews[0]["score"] == 85
    assert reviews[1]["decision"] == "MOVE"


def test_score_entry_with_mock():
    class FakeLLM:
        def complete(self, prompt, system=""):
            return '{"score": 45, "decision": "MOVE", "target_domain": "调拨", "reason": "包路径指向调拨"}'

    entry = {"class_name": "XxxImpl", "package": "com.example.transfer", "doc": "", "methods": ""}
    review = score_entry(FakeLLM(), entry, [])
    assert review["score"] == 45
    assert review["decision"] == "MOVE"
    assert review["target_domain"] == "调拨"
