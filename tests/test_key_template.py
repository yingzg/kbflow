from kbflow.scanners.key_template import extract_key_templates, normalize_key_pattern


class _FakeJavaFile:
    def __init__(self, content, class_name):
        self.content = content
        self.class_name = class_name
        self.path = "/fake"


def test_normalize_concat():
    assert normalize_key_pattern('"transfer:lock:" + transferNo') == "transfer:lock:{transferNo}"


def test_normalize_cache():
    assert normalize_key_pattern('"stock:cache:" + sku') == "stock:cache:{sku}"


def test_normalize_multi_concat():
    assert normalize_key_pattern('"order:" + orderNo + ":detail"') == "order:{orderNo}:detail"


def test_normalize_spel_braced():
    assert normalize_key_pattern("#{#sku}") == "{sku}"


def test_normalize_spel_bare():
    assert normalize_key_pattern("#sku") == "{sku}"


def test_normalize_upper_constant_stays_literal():
    assert normalize_key_pattern("STOCK_CACHE_KEY") == "STOCK_CACHE_KEY"


def test_extract_annotation_lock():
    jf = _FakeJavaFile(
        '@DistributedLock(keyPath = "transferNo", prefix = "transfer:lock", waitTime = 5)\n'
        "public void confirm(String transferNo) {}",
        "TransferManager",
    )
    results = extract_key_templates([jf])
    locks = [r for r in results if r["kind"] == "lock"]
    assert locks, "expected a lock entry"
    assert locks[0]["pattern"] == "transfer:lock:{transferNo}"
    assert locks[0]["class_name"] == "TransferManager"
    assert locks[0]["method_name"] == "confirm"


def test_extract_cache_call():
    jf = _FakeJavaFile(
        "public StockRecord getCached(String sku) {\n"
        '    redisTemplate.opsForValue().get("stock:cache:" + sku);\n'
        "    return null;\n"
        "}",
        "StockCacheManager",
    )
    results = extract_key_templates([jf])
    caches = [r for r in results if r["kind"] == "cache"]
    assert caches, "expected a cache entry"
    assert caches[0]["pattern"] == "stock:cache:{sku}"


def test_extract_shard():
    jf = _FakeJavaFile(
        "public int route(String transferNo) {\n    return transferNo.hashCode() % 8;\n}",
        "Router",
    )
    results = extract_key_templates([jf])
    shards = [r for r in results if r["kind"] == "shard"]
    assert shards, "expected a shard entry"
