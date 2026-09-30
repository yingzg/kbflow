import argparse

from kbflow.cli import _cmd_run


class MockLLM:
    def complete(self, prompt, system=""):
        if "领域驱动设计" in system:
            return (
                '[{"name": "调拨", "responsibility": "调拨单生命周期", "key_entities": ["调拨单"],'
                ' "boundary_included": ["审批"], "boundary_excluded": []}]'
            )
        if "评审" in system:
            return '{"score": 85, "decision": "KEEP", "target_domain": "调拨", "reason": "类名匹配"}'
        if "业务分析师" in system:
            return "调拨单"
        if "文档写作者" in system:
            return "该服务负责调拨单的全生命周期。"
        return "[]"


def test_run_wizard_auto(monkeypatch, tmp_path):
    monkeypatch.setattr("kbflow.cli.require_llm", lambda: MockLLM())
    src = tmp_path / "svc" / "src" / "main" / "java" / "com" / "example"
    src.mkdir(parents=True)
    (src / "TransferServiceImpl.java").write_text(
        "package com.example;\n@DubboService\n"
        "public class TransferServiceImpl implements TransferService {\n"
        "  public void approve(String no) {}\n}\n",
        encoding="utf-8",
    )
    (src / "TransferService.java").write_text(
        "package com.example;\n/** @Description 调拨服务 */\n"
        "public interface TransferService {\n  /** 审批 */ void approve(String no);\n}\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(project=str(tmp_path / "svc"), output=str(tmp_path / "kb"), auto=True)
    rc = _cmd_run(args)
    assert rc == 0
    assert (tmp_path / "kb" / "service-meta" / "behavior.toon").exists()
    assert (tmp_path / "kb" / "service-meta" / "domain_boundary_matrix.toon").exists()
    assert (tmp_path / "kb" / "调拨" / "svc" / "_overview.md").exists()
    assert (tmp_path / "kb" / "调拨" / "svc" / "_glossary.toon").exists()


def test_run_wizard_resume_skips_done_stages(monkeypatch, tmp_path):
    monkeypatch.setattr("kbflow.cli.require_llm", lambda: MockLLM())
    src = tmp_path / "svc" / "src" / "main" / "java" / "com" / "example"
    src.mkdir(parents=True)
    (src / "TransferServiceImpl.java").write_text(
        "package com.example;\n@DubboService\n"
        "public class TransferServiceImpl implements TransferService {\n"
        "  public void approve(String no) {}\n}\n",
        encoding="utf-8",
    )
    (src / "TransferService.java").write_text(
        "package com.example;\n/** @Description 调拨服务 */\n"
        "public interface TransferService {\n  /** 审批 */ void approve(String no);\n}\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(project=str(tmp_path / "svc"), output=str(tmp_path / "kb"), auto=True)
    assert _cmd_run(args) == 0

    def boom(*a, **k):
        raise AssertionError("K01 不应重跑")

    monkeypatch.setattr("kbflow.cli.run_scan", boom)
    assert _cmd_run(args) == 0
