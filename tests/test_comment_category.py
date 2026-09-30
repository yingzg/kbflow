from kbflow.scanners.comment_category import categorize


def test_cat_classification():
    entries = [
        {"doc": "有", "methods": [{"name": "a", "doc": "x"}, {"name": "b", "doc": "y"}]},
        {"doc": "有", "methods": [{"name": "a", "doc": "x"}, {"name": "b", "doc": ""}]},
        {"doc": "有", "methods": [{"name": "a", "doc": ""}]},
        {"doc": "", "methods": [{"name": "a", "doc": "x"}]},
        {"doc": "", "methods": [{"name": "a", "doc": ""}]},
    ]
    categorize(entries)
    assert [e["cat"] for e in entries] == ["cat1", "cat2", "cat3", "cat4", "cat5"]
