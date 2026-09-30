from enum import Enum


class GateLevel(Enum):
    AUTO_FIX = "auto_fix"
    HARD_BLOCK = "hard_block"
    WARN = "warn"
    HUMAN_REVIEW = "human_review"


class GateBlockedError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class GateResult:
    def __init__(self, level, message):
        self.level = level
        self.message = message

    def raise_if_blocked(self):
        if self.level == GateLevel.HARD_BLOCK:
            raise GateBlockedError(self.message)
        return self

    def __repr__(self):
        return "GateResult(%s, %r)" % (self.level.value, self.message)
