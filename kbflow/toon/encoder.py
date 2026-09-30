import math
import re

_DELIMITER = ","
_NUM_LOOKALIKE_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")


def _is_primitive(value):
    return value is None or isinstance(value, (bool, int, float, str))


def _looks_like_number(value):
    return bool(_NUM_LOOKALIKE_RE.match(value))


def is_safe_unquoted(value, delimiter=_DELIMITER):
    if not isinstance(value, str):
        return False
    if value == "":
        return False
    if value != value.strip():
        return False
    if value.lower() in ("true", "false", "null"):
        return False
    if _looks_like_number(value):
        return False
    if delimiter in value:
        return False
    if value.startswith("-"):
        return False
    for ch in value:
        if ch in ':"\\[]{}\n\r\t':
            return False
    return True


def _escape(value):
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _encode_string(value):
    if is_safe_unquoted(value):
        return value
    return '"' + _escape(value) + '"'


def _format_float(value):
    if math.isnan(value) or math.isinf(value):
        return "null"
    return repr(value)


def _encode_scalar(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_float(value)
    if isinstance(value, str):
        return _encode_string(value)
    raise TypeError("cannot encode value of type %s" % type(value).__name__)


def _union_keys(arr):
    keys = []
    for item in arr:
        for key in item:
            if key not in keys:
                keys.append(key)
    return keys


def _is_tabular(arr):
    for item in arr:
        if not isinstance(item, dict):
            return False
        for value in item.values():
            if not _is_primitive(value):
                return False
    return bool(_union_keys(arr))


def detect_tabular_header(arr):
    if not _is_tabular(arr):
        return None
    return _union_keys(arr)


def _encode_field(lines, key, value, indent, bullet):
    pad = "  " * indent
    if _is_primitive(value):
        scalar = _encode_scalar(value)
        if bullet:
            lines.append(pad + "- " + scalar)
        else:
            lines.append(pad + key + ": " + scalar)
        return
    if isinstance(value, dict):
        if not value:
            if bullet:
                lines.append(pad + "- ")
            else:
                lines.append(pad + key + ":")
            return
        if bullet:
            if not all(_is_primitive(v) for v in value.values()):
                raise TypeError("list items must be primitives or flat objects")
            parts = [k + ": " + _encode_scalar(v) for k, v in value.items()]
            lines.append(pad + "- " + ", ".join(parts))
            return
        lines.append(pad + key + ":")
        for sub_key, sub_value in value.items():
            _encode_field(lines, sub_key, sub_value, indent + 1, False)
        return
    if isinstance(value, list):
        _encode_array(lines, key, value, indent, bullet)
        return
    raise TypeError("cannot encode value of type %s" % type(value).__name__)


def _encode_array(lines, key, arr, indent, bullet):
    pad = "  " * indent
    count = len(arr)
    if bullet:
        raise TypeError("nested arrays as list items are not supported")
    if count == 0:
        lines.append(pad + key + "[0]:")
        return
    if _is_tabular(arr):
        fields = _union_keys(arr)
        lines.append(pad + key + "[%d]{%s}:" % (count, ",".join(fields)))
        row_indent = "  " * (indent + 1)
        for item in arr:
            cells = [_encode_scalar(item.get(f, "")) for f in fields]
            lines.append(row_indent + ",".join(cells))
        return
    if all(_is_primitive(x) for x in arr):
        cells = [_encode_scalar(x) for x in arr]
        lines.append(pad + key + "[%d]: %s" % (count, ",".join(cells)))
        return
    lines.append(pad + key + "[%d]:" % count)
    for item in arr:
        _encode_field(lines, None, item, indent, True)


def toon_dumps(obj):
    if not isinstance(obj, dict):
        raise TypeError("top-level value must be a dict")
    lines = []
    for key, value in obj.items():
        _encode_field(lines, key, value, 0, False)
    return "\n".join(lines)
