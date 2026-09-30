from kbflow.scanners.behavior import scan_behavior
from kbflow.scanners.topology import _find_impl, _is_interface, scan_topology


def test_injection_edge(make_index):
    idx = make_index({
        "TransferServiceImpl.java": (
            "package com.example;\n"
            "@DubboService\n"
            "public class TransferServiceImpl implements TransferService {\n"
            "  @Autowired private TransferManager manager;\n"
            "}\n"
        ),
        "TransferService.java": "package com.example;\npublic interface TransferService {}",
        "TransferManager.java": "package com.example;\npublic class TransferManager {}",
    })
    behavior = scan_behavior(idx)
    topo = scan_topology(idx, behavior, ["com.example"])
    assert len(topo["nodes"]["entries"]) == 1
    assert len(topo["nodes"]["services"]) == 1
    assert len(topo["edges"]["internal"]) == 1
    assert topo["edges"]["internal"][0]["kind"] == "injection"


def test_external_dubbo_reference_boundary(make_index):
    idx = make_index({
        "TransferServiceImpl.java": (
            "package com.example.wms;\n"
            "import com.example.stock.StockService;\n"
            "@DubboService\n"
            "public class TransferServiceImpl implements TransferService {\n"
            "  @DubboReference private StockService stockService;\n"
            "}\n"
        ),
        "TransferService.java": "package com.example.wms;\npublic interface TransferService {}",
    })
    behavior = scan_behavior(idx)
    topo = scan_topology(idx, behavior, ["com.example.wms"])
    assert len(topo["nodes"]["external"]) == 1
    assert len(topo["edges"]["external"]) == 1


def test_unresolved_recorded(make_index):
    idx = make_index({
        "TransferServiceImpl.java": (
            "package com.example;\n"
            "@DubboService\n"
            "public class TransferServiceImpl implements TransferService {\n"
            "  @Autowired private MissingDependency missing;\n"
            "}\n"
        ),
        "TransferService.java": "package com.example;\npublic interface TransferService {}",
    })
    behavior = scan_behavior(idx)
    topo = scan_topology(idx, behavior, ["com.example"])
    assert any(u["interface"] == "MissingDependency" for u in topo["unresolved"])


def test_find_impl_resolves_interface_to_implementation(make_index):
    idx = make_index({
        "BocAppService.java": "package com.acme;\npublic interface BocAppService {}",
        "BocAppServiceImpl.java": (
            "package com.acme;\n"
            "public class BocAppServiceImpl implements BocAppService {\n"
            "  @Resource private BocAppMapper bocAppMapper;\n"
            "}\n"
        ),
        "BocAppMapper.java": "package com.acme;\npublic interface BocAppMapper {}",
    })
    assert _find_impl(idx, "BocAppService") == "BocAppServiceImpl"
    assert _find_impl(idx, "BocAppMapper") == "BocAppMapper"


def test_topology_traces_through_service_to_mapper(make_index):
    idx = make_index({
        "BocAppProviderImpl.java": (
            "package com.acme;\n"
            "@DubboService\n"
            "public class BocAppProviderImpl {\n"
            "  @Resource private BocAppService bocAppService;\n"
            "}\n"
        ),
        "BocAppService.java": "package com.acme;\npublic interface BocAppService {}",
        "BocAppServiceImpl.java": (
            "package com.acme;\n"
            "public class BocAppServiceImpl implements BocAppService {\n"
            "  @Resource private BocAppMapper bocAppMapper;\n"
            "}\n"
        ),
        "BocAppMapper.java": "package com.acme;\npublic interface BocAppMapper {}",
    })
    behavior = scan_behavior(idx)
    topo = scan_topology(idx, behavior, ["com.acme"])
    service_classes = [n["class"] for n in topo["nodes"]["services"]]
    assert "BocAppServiceImpl" in service_classes
    assert "BocAppMapper" in service_classes


def test_is_interface_not_annotation():
    assert _is_interface("@interface MyAnnotation {}") is False
    assert _is_interface("public interface MyService {}") is True
    assert _is_interface("public class MyServiceImpl {}") is False


def test_find_impl_with_multiple_interfaces(make_index):
    idx = make_index({
        "A.java": "package com.acme;\npublic interface A {}",
        "B.java": "package com.acme;\npublic interface B {}",
        "Impl.java": "package com.acme;\npublic class Impl implements A, B {}",
    })
    assert _find_impl(idx, "A") == "Impl"
    assert _find_impl(idx, "B") == "Impl"


def test_find_impl_not_depend_on_naming_convention(make_index):
    idx = make_index({
        "OrderService.java": "package com.acme;\npublic interface OrderService {}",
        "OrderHandler.java": (
            "package com.acme;\n"
            "public class OrderHandler implements OrderService {}"
        ),
    })
    assert _find_impl(idx, "OrderService") == "OrderHandler"
