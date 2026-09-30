import pytest

from kbflow.gates.base import GateBlockedError, GateLevel, GateResult
from kbflow.gates.completeness import (
    check_count_conservation,
    check_no_placeholders,
    check_set_completeness,
)
from kbflow.gates.self_check import check_declared_counts


def test_self_check_autofix_count():
    text = "items[3]{id,name}:\n  1,a\n  2,b\n"
    fixed, fixes = check_declared_counts(text)
    assert fixed == "items[2]{id,name}:\n  1,a\n  2,b\n"
    assert fixes == ["items[3] -> 2"]


def test_self_check_no_fix_when_match():
    text = "items[2]{id,name}:\n  1,a\n  2,b\n"
    fixed, fixes = check_declared_counts(text)
    assert fixed == text
    assert fixes == []


def test_set_completeness_missing_blocks():
    result = check_set_completeness({"A", "B", "C"}, {"A", "B"})
    assert result.level == GateLevel.HARD_BLOCK
    with pytest.raises(GateBlockedError):
        result.raise_if_blocked()


def test_set_completeness_ok():
    result = check_set_completeness({"A", "B"}, {"A", "B"})
    assert result.level == GateLevel.AUTO_FIX


def test_count_conservation_blocks_on_mismatch():
    result = check_count_conservation(10, 9)
    assert result.level == GateLevel.HARD_BLOCK


def test_count_conservation_ok():
    result = check_count_conservation(10, 10)
    assert result.level == GateLevel.AUTO_FIX


def test_no_placeholders_blocks():
    result = check_no_placeholders("description: [待AI补充]")
    assert result.level == GateLevel.HARD_BLOCK


def test_no_placeholders_ok():
    result = check_no_placeholders("description: 调拨服务")
    assert result.level == GateLevel.AUTO_FIX


def test_gate_result_repr():
    r = GateResult(GateLevel.WARN, "截断告警")
    assert "warn" in repr(r)
