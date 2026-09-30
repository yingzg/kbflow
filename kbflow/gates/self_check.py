import re

_SECTION_RE = re.compile(r"^(\s*)(\w+)\[(\d+)\]\{(.+)\}:$")


def check_declared_counts(text):
    lines = text.split("\n")
    fixes = []
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _SECTION_RE.match(line)
        if not m:
            out.append(line)
            i += 1
            continue
        indent = m.group(1)
        key = m.group(2)
        declared = int(m.group(3))
        j = i + 1
        actual = 0
        while j < len(lines):
            nl = lines[j]
            if nl.strip() == "":
                j += 1
                continue
            if len(nl) - len(nl.lstrip(" ")) > len(indent):
                actual += 1
                j += 1
            else:
                break
        if actual != declared:
            fixes.append("%s[%d] -> %d" % (key, declared, actual))
            line = re.sub(r"\[(\d+)\]", "[%d]" % actual, line, count=1)
        out.append(line)
        out.extend(lines[i + 1:j])
        i = j
    return "\n".join(out), fixes
