from kbflow.scanners.dependency import scan_external_dependencies


def test_dubbo_reference_external(make_index):
    idx = make_index({
        "OrderManager.java": (
            "package com.example.wms;\n"
            "import com.example.stock.StockService;\n"
            "public class OrderManager {\n"
            "  @DubboReference private StockService stockService;\n"
            "}\n"
        ),
    })
    result = scan_external_dependencies(idx, ["com.example.wms"])
    assert len(result["interfaces"]) == 1
    assert result["interfaces"][0]["name"] == "StockService"
    assert result["interfaces"][0]["package"] == "com.example.stock"
    assert result["by_annotation"][0]["class"] == "OrderManager"


def test_xml_reference(make_index):
    idx = make_index({
        "dubbo-consumer.xml": (
            "<dubbo:reference id=\"stockService\" interface=\"com.example.stock.StockService\" />\n"
        ),
    })
    result = scan_external_dependencies(idx, ["com.example.wms"])
    assert len(result["interfaces"]) == 1
    assert result["by_xml"][0]["xml_file"] == "dubbo-consumer.xml"


def test_same_interface_referenced_twice(make_index):
    idx = make_index({
        "A.java": (
            "package com.example;\nimport com.example.stock.StockService;\n"
            "public class A {\n  @DubboReference private StockService stockService;\n}\n"
        ),
        "B.java": (
            "package com.example;\nimport com.example.stock.StockService;\n"
            "public class B {\n  @DubboReference private StockService stockService;\n}\n"
        ),
    })
    result = scan_external_dependencies(idx, ["com.example"])
    assert len(result["interfaces"]) == 1
    for a in result["by_annotation"]:
        assert isinstance(a["interface_ref"], str)
