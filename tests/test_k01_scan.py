from kbflow.stages.k01_scan import run_scan
from kbflow.toon import toon_loads


def test_run_scan_end_to_end(tmp_path):
    src = tmp_path / "demo" / "src" / "main" / "java" / "com" / "example"
    src.mkdir(parents=True)
    (src / "TransferServiceImpl.java").write_text(
        "package com.example;\n"
        "@DubboService\n"
        "public class TransferServiceImpl implements TransferService {\n"
        "  public void approve(String no) {}\n"
        "}\n",
        encoding="utf-8",
    )
    (src / "TransferService.java").write_text(
        "package com.example;\n"
        "/** @Description 调拨服务 */\n"
        "public interface TransferService {\n"
        "  /** 审批 */ void approve(String no);\n"
        "}\n",
        encoding="utf-8",
    )
    output = tmp_path / "kb"
    result = run_scan(tmp_path / "demo", output)
    assert result["entry_count"] == 1
    text = (output / "service-meta" / "behavior.toon").read_text(encoding="utf-8")
    obj = toon_loads(text)
    assert obj["metadata"]["entry_count"] == 1
    assert obj["dubbo"]["with_doc"][0]["doc"] == "调拨服务"
