from kbflow.stages.k03_confirm import (
    apply_decision,
    classify_by_score,
    markdown_to_reviews,
    reviews_to_markdown,
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
