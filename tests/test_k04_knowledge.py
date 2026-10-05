from kbflow.scanners.sql_tables import extract_tables_from_sql, extract_tables_from_xml
from kbflow.stages.k04_knowledge import (
    PLACEHOLDER,
    generate_data_model_skeleton,
    generate_interface_skeleton,
    generate_overview_skeleton,
)


def test_skeleton_bucket_a_and_c():
    entries = [
        {"id": "API-001", "class_name": "TransferServiceImpl", "kind": "dubbo",
         "doc": "创建调拨单", "methods": ""},
    ]
    skeleton = generate_overview_skeleton("调拨", "transfer-service", entries)
    assert skeleton["service_info"]["name"] == "transfer-service"
    assert skeleton["service_info"]["domain"] == "调拨"
    assert skeleton["service_info"]["description"] == PLACEHOLDER
    assert skeleton["scenarios"]["P0"][0]["trigger"] == "dubbo"
    assert skeleton["scenarios"]["P0"][0]["desc"] == PLACEHOLDER


def test_priority_clustering():
    entries = [
        {"id": "API-001", "class_name": "DubboImpl", "kind": "dubbo", "doc": "", "methods": ""},
        {"id": "API-002", "class_name": "Controller", "kind": "rest", "doc": "", "methods": ""},
        {"id": "API-003", "class_name": "Job", "kind": "job", "doc": "", "methods": ""},
    ]
    skeleton = generate_overview_skeleton("调拨", "svc", entries)
    assert len(skeleton["scenarios"]["P0"]) == 1
    assert len(skeleton["scenarios"]["P1"]) == 1
    assert len(skeleton["scenarios"]["P2"]) == 1


def test_interface_skeleton_entry_tables():
    entries = [
        {"id": "API-001", "class_name": "TransferServiceImpl", "kind": "dubbo", "doc": "", "methods": ""},
    ]
    topology = {
        "nodes": {
            "entries": [{"id": "N1", "class": "TransferServiceImpl", "type": "dubbo_provider"}],
            "services": [{"id": "S1", "class": "TransferOrderMapper", "pkg": ""}],
            "external": [],
        },
        "edges": {
            "internal": [{"from": "N1", "to": "S1", "kind": "injection"}],
            "external": [],
        },
    }
    tables = [{"name": "transfer_order", "ddl": "CREATE TABLE transfer_order (...);"}]
    interface = generate_interface_skeleton(entries, topology, tables)
    assert len(interface["api_entries"]) == 1
    assert interface["entry_tables"][0]["tables"] == "transfer_order"


def test_data_model_table_class_map():
    tables = [{"name": "transfer_order", "ddl": "CREATE TABLE transfer_order (...);"}]
    entry_tables = [{"entry_id": "API-001", "tables": "transfer_order"}]
    entries = [{"id": "API-001", "class_name": "TransferServiceImpl"}]
    data_model = generate_data_model_skeleton(tables, entry_tables, entries)
    assert data_model["table_class_map"][0]["table"] == "transfer_order"
    assert "TransferServiceImpl" in data_model["table_class_map"][0]["entry_classes"]


def test_extract_tables_from_sql():
    content = (
        '@Select("SELECT * FROM acme_order WHERE id = #{id}")\n'
        'int select(String id);\n'
        '@Insert("INSERT INTO acme_order_item (a) VALUES (#{a})")\n'
        'int insert(X x);\n'
        '@Select("SELECT a, b FROM acme_order p JOIN acme_order_item i ON p.id=i.pid")\n'
    )
    tables = extract_tables_from_sql(content)
    assert "acme_order" in tables
    assert "acme_order_item" in tables


def test_extract_tables_from_xml():
    xml = (
        '<mapper namespace="com.example.AccountStatementPackageMapper">\n'
        '  <select id="countByAcmeCode">\n'
        '    select count(1) from acme_account_package where acme_code = #{code}\n'
        '  </select>\n'
        '</mapper>'
    )
    tables = extract_tables_from_xml(xml)
    assert "acme_account_package" in tables
