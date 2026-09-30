from kbflow.scanners.ddl import extract_tables


def test_extract_with_anchors():
    ddl = (
        "-- TABLE: transfer_order\n"
        "CREATE TABLE transfer_order (transfer_no VARCHAR(64));\n"
        "-- TABLE: stock_record\n"
        "CREATE TABLE stock_record (sku VARCHAR(64));\n"
    )
    tables = extract_tables(ddl)
    assert [t["name"] for t in tables] == ["transfer_order", "stock_record"]


def test_extract_without_anchor():
    tables = extract_tables("CREATE TABLE foo (id INT);")
    assert tables == [{"name": "foo", "ddl": "CREATE TABLE foo (id INT);"}]


def test_anchor_name_wins_over_create_name():
    tables = extract_tables("-- TABLE: my_table\nCREATE TABLE actual_name (id INT);")
    assert tables[0]["name"] == "my_table"


def test_ignores_comment_only_sections():
    tables = extract_tables("-- header comment\n\n-- TABLE: a\nCREATE TABLE a (id INT);")
    assert len(tables) == 1


def test_empty():
    assert extract_tables("") == []
