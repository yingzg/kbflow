import re

_KEY = r"[^\s\[\]\{\}:,]+"
_TABULAR_RE = re.compile(r"^(" + _KEY + r")\[(\d+)\]\{([^}]*)\}:\s*$")
_ARRAY_RE = re.compile(r"^(" + _KEY + r")\[(\d+)\]:\s*(.*)$")
_SCALAR_RE = re.compile(r"^(" + _KEY + r"):\s*(.*)$")
_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?$")


class ToonDecodeError(ValueError):
    pass


def _unescape(value):
    out = []
    i = 0
    n = len(value)
    while i < n:
        ch = value[i]
        if ch == "\\" and i + 1 < n:
            nxt = value[i + 1]
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            if nxt == "r":
                out.append("\r")
                i += 2
                continue
            if nxt == "t":
                out.append("\t")
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
            if nxt == '"':
                out.append('"')
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _parse_scalar(value):
    value = value.strip()
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return _unescape(value[1:-1])
    if _INT_RE.match(value):
        return int(value)
    if _FLOAT_RE.match(value) and ("." in value or "e" in value or "E" in value):
        return float(value)
    return value


def _split_csv(value):
    parts = []
    cur = []
    in_quote = False
    i = 0
    n = len(value)
    while i < n:
        ch = value[i]
        if in_quote:
            if ch == "\\" and i + 1 < n:
                cur.append(ch)
                cur.append(value[i + 1])
                i += 2
                continue
            if ch == '"':
                in_quote = False
                cur.append(ch)
                i += 1
                continue
            cur.append(ch)
            i += 1
            continue
        if ch == '"':
            in_quote = True
            cur.append(ch)
            i += 1
            continue
        if ch == ",":
            parts.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def _has_unquoted(value, target):
    in_quote = False
    i = 0
    n = len(value)
    while i < n:
        ch = value[i]
        if in_quote:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == '"':
                in_quote = False
            i += 1
            continue
        if ch == '"':
            in_quote = True
            i += 1
            continue
        if ch == target:
            return True
        i += 1
    return False


def _leading_ws(line):
    i = 0
    width = 0
    has_tab = False
    while i < len(line):
        ch = line[i]
        if ch == " ":
            width += 1
            i += 1
        elif ch == "\t":
            has_tab = True
            width += 2
            i += 1
        else:
            break
    return i, width, has_tab


def _parse_list_item(content):
    content = content.strip()
    if content == "":
        return {}
    if _has_unquoted(content, ":"):
        result = {}
        for part in _split_csv(content):
            key, _, rest = part.partition(":")
            result[key.strip()] = _parse_scalar(rest.strip())
        return result
    return _parse_scalar(content)


def _parse_tabular(lines, idx, match, result, indent, strict):
    key = match.group(1)
    count = int(match.group(2))
    fields = [f.strip() for f in match.group(3).split(",") if f.strip()]
    rows = []
    i = idx + 1
    n = len(lines)
    row_indent = indent + 2
    while len(rows) < count:
        if i >= n:
            break
        line = lines[i]
        if line.strip() == "":
            if strict:
                raise ToonDecodeError("empty line inside tabular array")
            i += 1
            continue
        char_count, width, has_tab = _leading_ws(line)
        if has_tab and strict:
            raise ToonDecodeError("tab indentation in tabular array")
        if width < row_indent:
            break
        if width > row_indent:
            if strict:
                raise ToonDecodeError("unexpected indentation in tabular array")
            break
        cells = _split_csv(line[char_count:])
        if len(cells) != len(fields):
            raise ToonDecodeError(
                "%s: row has %d cells, expected %d" % (key, len(cells), len(fields))
            )
        row = {}
        for field, cell in zip(fields, cells):
            row[field] = _parse_scalar(cell.strip())
        rows.append(row)
        i += 1
    if strict and len(rows) != count:
        raise ToonDecodeError(
            "%s: declared [%d] but found %d rows" % (key, count, len(rows))
        )
    result[key] = rows
    return i


def _parse_array(lines, idx, match, result, indent, strict):
    key = match.group(1)
    count = int(match.group(2))
    rest = match.group(3).strip()
    if count == 0:
        result[key] = []
        return idx + 1
    if rest:
        items = [_parse_scalar(x.strip()) for x in _split_csv(rest)]
        if strict and len(items) != count:
            raise ToonDecodeError(
                "%s: declared [%d] but found %d items" % (key, count, len(items))
            )
        result[key] = items
        return idx + 1
    arr = []
    i = idx + 1
    n = len(lines)
    while len(arr) < count:
        if i >= n:
            break
        line = lines[i]
        if line.strip() == "":
            if strict:
                raise ToonDecodeError("empty line inside array")
            i += 1
            continue
        char_count, width, has_tab = _leading_ws(line)
        if has_tab and strict:
            raise ToonDecodeError("tab indentation in array")
        if width < indent:
            break
        if width > indent:
            if strict:
                raise ToonDecodeError("unexpected indentation in array")
            break
        item_text = line[char_count:]
        if not item_text.startswith("- "):
            break
        arr.append(_parse_list_item(item_text[2:]))
        i += 1
    if strict and len(arr) != count:
        raise ToonDecodeError(
            "%s: declared [%d] but found %d items" % (key, count, len(arr))
        )
    result[key] = arr
    return i


def _parse_key_line(lines, idx, key_line, result, indent, strict):
    match = _TABULAR_RE.match(key_line)
    if match:
        return _parse_tabular(lines, idx, match, result, indent, strict)
    match = _ARRAY_RE.match(key_line)
    if match:
        return _parse_array(lines, idx, match, result, indent, strict)
    match = _SCALAR_RE.match(key_line)
    if match:
        key = match.group(1)
        rest = match.group(2)
        if rest == "":
            sub, next_idx = _parse_block(lines, idx + 1, indent + 2, strict)
            result[key] = sub
            return next_idx
        result[key] = _parse_scalar(rest)
        return idx + 1
    raise ToonDecodeError("cannot parse line %d: %r" % (idx + 1, key_line))


def _parse_block(lines, idx, indent, strict):
    result = {}
    n = len(lines)
    while idx < n:
        line = lines[idx]
        if line.strip() == "":
            idx += 1
            continue
        char_count, width, has_tab = _leading_ws(line)
        if has_tab and strict:
            raise ToonDecodeError("tab indentation at line %d" % (idx + 1))
        if width < indent:
            break
        if width > indent:
            raise ToonDecodeError("unexpected indentation at line %d" % (idx + 1))
        idx = _parse_key_line(lines, idx, line[char_count:], result, indent, strict)
    return result, idx


def toon_loads(text, strict=True):
    if text is None:
        return {}
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    result, _ = _parse_block(lines, 0, 0, strict)
    return result
