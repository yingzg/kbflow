from kbflow.scanners.file_index import FileIndex


def test_scan_and_find(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Foo.java").write_text(
        "package com.example;\npublic class Foo {}\n", encoding="utf-8"
    )
    idx = FileIndex(tmp_path)
    assert len(idx.all_files()) == 1
    f = idx.find_by_class_name("Foo")
    assert f is not None
    assert f.package == "com.example"


def test_skips_test_and_target_dirs(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Foo.java").write_text("public class Foo {}", encoding="utf-8")
    (tmp_path / "src" / "test").mkdir()
    (tmp_path / "src" / "test" / "FooTest.java").write_text("public class FooTest {}", encoding="utf-8")
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "Gen.java").write_text("public class Gen {}", encoding="utf-8")
    idx = FileIndex(tmp_path)
    names = {f.class_name for f in idx.all_files()}
    assert names == {"Foo"}


def test_skips_test_named_classes(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Foo.java").write_text("public class Foo {}", encoding="utf-8")
    (tmp_path / "src" / "FooTest.java").write_text("public class FooTest {}", encoding="utf-8")
    (tmp_path / "src" / "FooTests.java").write_text("public class FooTests {}", encoding="utf-8")
    idx = FileIndex(tmp_path)
    names = {f.class_name for f in idx.all_files()}
    assert names == {"Foo"}


def test_internal_prefixes(tmp_path):
    (tmp_path / "pom.xml").write_text(
        "<project><parent><groupId>com.example.wms</groupId></parent>"
        "<groupId>com.example.wms</groupId></project>",
        encoding="utf-8",
    )
    idx = FileIndex(tmp_path)
    assert "com.example.wms" in idx.internal_prefixes()


def test_internal_prefixes_from_package_when_groupid_differs(tmp_path):
    (tmp_path / "pom.xml").write_text(
        "<project><groupId>com.example.wms</groupId></project>",
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Foo.java").write_text(
        "package com.acme.order;\npublic class Foo {}", encoding="utf-8"
    )
    (tmp_path / "src" / "Bar.java").write_text(
        "package com.acme.order;\npublic class Bar {}", encoding="utf-8"
    )
    idx = FileIndex(tmp_path)
    assert idx.internal_prefixes() == ["com.acme.order"]
