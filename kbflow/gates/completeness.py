from kbflow.gates.base import GateLevel, GateResult

_DEFAULT_PLACEHOLDER = "[待AI补充]"


def check_set_completeness(discovered, documented, label="入口"):
    missing = set(discovered) - set(documented)
    if missing:
        preview = sorted(missing)[:5]
        return GateResult(
            GateLevel.HARD_BLOCK,
            "%s完整性失败: %d 个未进文档 %s" % (label, len(missing), preview),
        )
    return GateResult(GateLevel.AUTO_FIX, "%s完整性通过 (%d 个)" % (label, len(documented)))


def check_count_conservation(before, after, label="切分"):
    if before != after:
        return GateResult(
            GateLevel.HARD_BLOCK,
            "%s数量不守恒: 切分前 %d != 切分后 %d" % (label, before, after),
        )
    return GateResult(GateLevel.AUTO_FIX, "%s守恒通过 (%d)" % (label, before))


def check_no_placeholders(text, placeholder=_DEFAULT_PLACEHOLDER):
    if placeholder in text:
        return GateResult(GateLevel.HARD_BLOCK, "存在未补充的语义占位符 %s" % placeholder)
    return GateResult(GateLevel.AUTO_FIX, "无占位符残留")
