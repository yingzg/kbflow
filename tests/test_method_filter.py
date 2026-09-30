from kbflow.scanners.method_filter import classify_method, filter_methods


def test_tostring_hard_skip():
    assert classify_method("toString", [], set(), False) == "hard_skip"


def test_approve_order_priority_without_doc():
    assert classify_method("approveOrder", [], set(), False) == "priority"


def test_get_stock_list_no_field_is_normal():
    assert classify_method("getStockList", [], set(), False) == "normal"


def test_get_name_with_field_deprioritize():
    assert classify_method("getName", [], {"name"}, False) == "deprioritize"


def test_check_stock_with_param_normal():
    assert classify_method("checkStock", ["sku", "qty"], set(), False) == "normal"


def test_check_no_param_deprioritize():
    assert classify_method("check", [], set(), False) == "deprioritize"


def test_filter_methods_truncates_and_warns():
    methods = [{"name": "method%d" % i, "params": [], "doc": ""} for i in range(53)]
    kept, truncated = filter_methods(methods, set(), max_keep=20)
    assert len(kept) == 20
    assert len(truncated) == 33


def test_filter_methods_orders_priority_first():
    methods = [
        {"name": "getName", "params": [], "doc": ""},
        {"name": "approveOrder", "params": [], "doc": ""},
        {"name": "getStockList", "params": [], "doc": ""},
    ]
    kept, _ = filter_methods(methods, {"name"}, max_keep=20)
    assert kept[0]["name"] == "approveOrder"


def test_filter_methods_drops_hard_skip():
    methods = [
        {"name": "toString", "params": [], "doc": ""},
        {"name": "confirm", "params": [], "doc": ""},
    ]
    kept, _ = filter_methods(methods, set(), max_keep=20)
    assert [m["name"] for m in kept] == ["confirm"]
