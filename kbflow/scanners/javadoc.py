import re

_TAG_RE = re.compile(r"@\w+")
_HTML_RE = re.compile(r"<[^>]+>")
_DATE_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")
_DATE_PREFIX_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}[\s:：-]*")


def clean_javadoc(raw):
    if not raw:
        return ""
    text = re.sub(r"/\*\*?|\*/", "", raw)
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("*"):
            line = line[1:].strip()
        if line:
            lines.append(line)
    text = " ".join(lines).strip()

    m = re.search(r"@Description\s*[:：]?\s*([^\n@]+)", text)
    if m:
        text = m.group(1).strip()
    else:
        m = _TAG_RE.search(text)
        if m:
            text = text[: m.start()].strip()

    text = _HTML_RE.sub("", text).strip()
    if len(text) < 2:
        return ""
    if _DATE_RE.match(text):
        return ""
    text = _DATE_PREFIX_RE.sub("", text).strip()
    if len(text) < 2:
        return ""
    if len(text) > 120:
        text = text[:120]
    return text


def extract_class_doc(content, class_decl_start):
    prefix = content[max(0, class_decl_start - 1000):class_decl_start]
    m = list(re.finditer(r"/\*\*", prefix))
    if not m:
        return ""
    start = m[-1].start()
    end = prefix.find("*/", start)
    if end == -1:
        return ""
    return clean_javadoc(prefix[start:end + 2])


def extract_method_doc(content, method_start):
    prefix = content[max(0, method_start - 500):method_start]
    m = list(re.finditer(r"/\*\*", prefix))
    if not m:
        return ""
    start = m[-1].start()
    end = prefix.find("*/", start)
    if end == -1:
        return ""
    return clean_javadoc(prefix[start:end + 2])
