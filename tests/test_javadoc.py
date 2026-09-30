from kbflow.scanners.javadoc import clean_javadoc


def test_description_priority():
    assert clean_javadoc("/** @Description 创建调拨单 */") == "创建调拨单"


def test_author_noise_removed():
    assert clean_javadoc("/** @author zhangsan 创建 */") == ""


def test_strips_stars_and_html():
    assert clean_javadoc("/**\n * 调拨单 <b>实体</b>\n */") == "调拨单 实体"


def test_pure_date_dropped():
    assert clean_javadoc("/** 2024-01-01 */") == ""


def test_truncate_long():
    long_text = "很" * 200
    result = clean_javadoc("/** " + long_text + " */")
    assert len(result) == 120


def test_empty():
    assert clean_javadoc("") == ""
