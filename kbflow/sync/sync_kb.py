import hashlib
from pathlib import Path

MAPPINGS = {
    "stages": {"source": "kbflow/stages", "target": ".kbflow/stages"},
    "scanners": {"source": "kbflow/scanners", "target": ".kbflow/scanners"},
    "gates": {"source": "kbflow/gates", "target": ".kbflow/gates"},
    "toon": {"source": "kbflow/toon", "target": ".kbflow/toon"},
    "glossary": {"source": "kbflow/glossary", "target": ".kbflow/glossary"},
    "sync": {"source": "kbflow/sync", "target": ".kbflow/sync"},
    "entry": {"source": "kbflow.py", "target": ".kbflow/kbflow.py"},
}


def file_hash(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def files_identical(source, target):
    if source.stat().st_size != target.stat().st_size:
        return False
    return file_hash(source) == file_hash(target)


def sync_directory(source_dir, target_dir):
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    stats = {"copied": [], "updated": [], "skipped": []}
    if not source_dir.is_dir():
        return stats
    target_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(source_dir.rglob("*")):
        if src.is_dir() or "__pycache__" in src.parts:
            continue
        rel = src.relative_to(source_dir)
        dst = target_dir / rel
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            stats["copied"].append(str(rel))
        elif not files_identical(src, dst):
            dst.write_bytes(src.read_bytes())
            stats["updated"].append(str(rel))
        else:
            stats["skipped"].append(str(rel))
    return stats


def detect_orphans(source_dir, target_dir):
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    orphans = []
    if not target_dir.is_dir():
        return orphans
    source_files = {p.relative_to(source_dir) for p in source_dir.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    for p in target_dir.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            rel = p.relative_to(target_dir)
            if rel not in source_files:
                orphans.append(str(rel))
    return orphans


def sync_to_kb(framework_dir, kb_dir, strict=False):
    framework_dir = Path(framework_dir)
    kb_dir = Path(kb_dir)
    report = {}
    for name, mapping in MAPPINGS.items():
        src = framework_dir / mapping["source"]
        dst = kb_dir / mapping["target"]
        if src.is_dir():
            report[name] = sync_directory(src, dst)
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or not files_identical(src, dst):
                dst.write_bytes(src.read_bytes())
                report[name] = {"copied": [mapping["source"]], "updated": [], "skipped": []}
    orphans = {}
    for name, mapping in MAPPINGS.items():
        src = framework_dir / mapping["source"]
        dst = kb_dir / mapping["target"]
        if src.is_dir():
            o = detect_orphans(src, dst)
            if o:
                orphans[name] = o
                if strict:
                    for rel in o:
                        (dst / rel).unlink(missing_ok=True)
    return {"report": report, "orphans": orphans}
