from kbflow.scanners.sql_tables import (
    extract_mapper_tables,
    extract_tables_from_annotations,
    extract_tables_from_xml,
)


def test_extract_tables_from_annotations_generic():
    content = (
        '@Select("SELECT * FROM acme_order WHERE id = #{id}")\n'
        'int select(String id);\n'
    )
    tables = extract_tables_from_annotations(content)
    assert "acme_order" in tables


def test_extract_tables_from_xml_generic():
    xml = (
        '<mapper namespace="com.acme.order.OrderMapper">\n'
        '  <select id="list">select * from acme_order_item where order_id = #{id}</select>\n'
        '  <insert id="insert">insert into acme_order_log (id) values (#{id})</insert>\n'
        '</mapper>'
    )
    tables = extract_tables_from_xml(xml)
    assert "acme_order_item" in tables
    assert "acme_order_log" in tables


def test_extract_mapper_tables_from_generic_project(make_index):
    idx = make_index({
        "src/main/java/com/acme/order/OrderMapper.java": (
            "package com.acme.order;\n"
            "import org.apache.ibatis.annotations.Mapper;\n"
            "@Mapper\n"
            "public interface OrderMapper {\n"
            '  @Select("SELECT * FROM acme_order WHERE id = #{id}") int select(String id);\n'
            "}\n"
        ),
        "src/main/resources/mapper/OrderMapper.xml": (
            '<mapper namespace="com.acme.order.OrderMapper">\n'
            '  <select id="list">select * from acme_order_item where order_id = #{id}</select>\n'
            '</mapper>'
        ),
    })
    result = extract_mapper_tables(idx)
    assert "OrderMapper" in result
    assert "acme_order" in result["OrderMapper"]
    assert "acme_order_item" in result["OrderMapper"]
