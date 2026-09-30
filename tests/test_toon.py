import pytest

from kbflow.toon import ToonDecodeError, toon_dumps, toon_loads


REFERENCE_OBJ = {
    "context": {"task": "徒步记录", "location": "Boulder"},
    "friends": ["ana", "luis"],
    "hikes": [
        {"id": 1, "name": "Blue Lake", "km": 7.5},
        {"id": 2, "name": "Ridge", "km": 9.2},
    ],
}

REFERENCE_TOON = (
    "context:\n"
    "  task: 徒步记录\n"
    "  location: Boulder\n"
    "friends[2]: ana,luis\n"
    "hikes[2]{id,name,km}:\n"
    "  1,Blue Lake,7.5\n"
    "  2,Ridge,9.2"
)


def test_reference_exact_encoding():
    assert toon_dumps(REFERENCE_OBJ) == REFERENCE_TOON


def test_reference_roundtrip():
    assert toon_loads(toon_dumps(REFERENCE_OBJ)) == REFERENCE_OBJ


def test_tabular_array_roundtrip():
    obj = {
        "hikes": [
            {"id": 1, "name": "Blue Lake", "km": 7.5},
            {"id": 2, "name": "Ridge", "km": 9.2},
        ]
    }
    text = toon_dumps(obj)
    assert text == "hikes[2]{id,name,km}:\n  1,Blue Lake,7.5\n  2,Ridge,9.2"
    assert toon_loads(text) == obj


def test_inline_primitive_array_roundtrip():
    obj = {"tags": ["a", "b", "c"]}
    assert toon_dumps(obj) == "tags[3]: a,b,c"
    assert toon_loads("tags[3]: a,b,c") == obj


def test_mixed_array_roundtrip():
    obj = {"items": [1, "some string", {"key": "value"}]}
    text = toon_dumps(obj)
    assert text == "items[3]:\n- 1\n- some string\n- key: value"
    assert toon_loads(text) == obj


def test_quoting_true_string_gets_quoted():
    assert toon_dumps({"a": "true"}) == 'a: "true"'


def test_quoting_hello_world_not_quoted():
    assert toon_dumps({"a": "Hello World"}) == "a: Hello World"


def test_quoting_empty_string():
    assert toon_dumps({"a": ""}) == 'a: ""'


def test_quoting_leading_trailing_whitespace():
    assert toon_dumps({"a": " x "}) == 'a: " x "'


def test_quoting_number_lookalike():
    assert toon_dumps({"a": "123"}) == 'a: "123"'
    assert toon_dumps({"a": "1.5"}) == 'a: "1.5"'


def test_quoting_contains_colon():
    assert toon_dumps({"a": "a:b"}) == 'a: "a:b"'


def test_quoting_contains_comma():
    assert toon_dumps({"a": "a,b"}) == 'a: "a,b"'


def test_quoting_starts_with_dash():
    assert toon_dumps({"a": "-x"}) == 'a: "-x"'


def test_quoting_internal_space_and_cjk_safe():
    assert toon_dumps({"a": "Hello World"}) == "a: Hello World"
    assert toon_dumps({"a": "徒步记录"}) == "a: 徒步记录"
    assert toon_dumps({"a": "single'quote#hash"}) == "a: single'quote#hash"


def test_quoting_escapes():
    assert toon_dumps({"a": 'say "hi"'}) == 'a: "say \\"hi\\""'
    assert toon_dumps({"a": "back\\slash"}) == 'a: "back\\\\slash"'


def test_escape_roundtrip():
    obj = {"a": 'line1\nline2\ttab\rreturn "quote" \\ back'}
    assert toon_loads(toon_dumps(obj)) == obj


def test_strict_count_mismatch_tabular():
    text = "hikes[3]{id,name,km}:\n  1,Blue Lake,7.5\n  2,Ridge,9.2\n"
    with pytest.raises(ToonDecodeError):
        toon_loads(text, strict=True)


def test_strict_count_mismatch_inline():
    text = "tags[3]: a,b\n"
    with pytest.raises(ToonDecodeError):
        toon_loads(text, strict=True)


def test_strict_tab_indentation():
    text = "context:\n\ttask: foo\n"
    with pytest.raises(ToonDecodeError):
        toon_loads(text, strict=True)


def test_strict_empty_line_inside_array():
    text = "hikes[2]{id,name}:\n  1,a\n\n  2,b\n"
    with pytest.raises(ToonDecodeError):
        toon_loads(text, strict=True)


def test_nested_object_roundtrip():
    obj = {"context": {"task": "徒步记录", "location": "Boulder"}}
    assert toon_dumps(obj) == "context:\n  task: 徒步记录\n  location: Boulder"
    assert toon_loads(toon_dumps(obj)) == obj


def test_deeply_nested_roundtrip():
    obj = {"a": {"b": {"c": {"d": 1}}}}
    assert toon_loads(toon_dumps(obj)) == obj


def test_scalar_types_roundtrip():
    obj = {"i": 42, "f": 3.14, "t": True, "n": None, "s": "hi"}
    assert toon_loads(toon_dumps(obj)) == obj


def test_empty_array_roundtrip():
    obj = {"friends": []}
    assert toon_dumps(obj) == "friends[0]:"
    assert toon_loads("friends[0]:") == obj


def test_empty_object_roundtrip():
    obj = {"context": {}}
    assert toon_dumps(obj) == "context:"
    assert toon_loads("context:") == obj


def test_tabular_with_missing_field_fills_empty():
    obj = {
        "hikes": [
            {"id": 1, "name": "Blue Lake", "km": 7.5},
            {"id": 2, "name": "Ridge"},
        ]
    }
    text = toon_dumps(obj)
    assert text == 'hikes[2]{id,name,km}:\n  1,Blue Lake,7.5\n  2,Ridge,""'
    assert toon_loads(text) == {
        "hikes": [
            {"id": 1, "name": "Blue Lake", "km": 7.5},
            {"id": 2, "name": "Ridge", "km": ""},
        ]
    }


def test_multi_key_object_in_list_roundtrip():
    obj = {"items": [{"key": "value", "other": 2}]}
    assert toon_loads(toon_dumps(obj)) == obj


def test_non_strict_tolerates_tab():
    text = "context:\n\ttask: foo\n"
    assert toon_loads(text, strict=False) == {"context": {"task": "foo"}}


def test_non_strict_tolerates_count_mismatch():
    text = "hikes[3]{id,name}:\n  1,a\n  2,b\n"
    assert toon_loads(text, strict=False) == {
        "hikes": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
    }


def test_empty_text_returns_empty_dict():
    assert toon_loads("") == {}
    assert toon_loads("   \n\n") == {}
