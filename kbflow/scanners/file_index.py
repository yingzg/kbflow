import re
from dataclasses import dataclass
from pathlib import Path

_SKIP_DIRS = {"test", "tests", "target"}
_FRAMEWORK_GROUPS = {"org.springframework.boot", "org.springframework.cloud"}
_PACKAGE_RE = re.compile(r"package\s+([\w.]+)\s*;")
_CLASS_RE = re.compile(r"\b(?:public\s+)?(?:abstract\s+|final\s+)?(?:class|interface|enum)\s+(\w+)")


def _common_package_prefix(packages):
    from collections import Counter

    counter = Counter()
    for p in packages:
        parts = p.split(".")
        for n in range(2, min(len(parts), 5) + 1):
            counter[".".join(parts[:n])] += 1
    total = len(packages)
    best = ""
    for prefix, count in counter.items():
        if count >= total * 0.6 and len(prefix) > len(best):
            best = prefix
    return best


@dataclass
class JavaFile:
    path: Path
    content: str
    package: str
    class_name: str


class FileIndex:
    def __init__(self, project_dir, on_progress=None):
        self.project_dir = Path(project_dir)
        self._on_progress = on_progress
        self._files = self._scan()
        self._by_name = {}
        for f in self._files:
            self._by_name.setdefault(f.class_name, f)
        self._implements = self._build_implements_index()

    def _build_implements_index(self):
        idx = {}
        for f in self._files:
            m = re.search(r"\bclass\s+\w+\s+implements\s+([\w,\s<>]+?)\s*\{", f.content)
            if not m:
                continue
            for iface in re.findall(r"\w+", m.group(1)):
                idx.setdefault(iface, []).append(f.class_name)
        return idx

    def _scan(self):
        files = []
        count = 0
        for path in self.project_dir.rglob("*.java"):
            try:
                rel_parts = path.relative_to(self.project_dir).parts
            except ValueError:
                continue
            if any(part in _SKIP_DIRS for part in rel_parts):
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except (OSError, PermissionError):
                continue
            package = ""
            m = _PACKAGE_RE.search(content)
            if m:
                package = m.group(1)
            class_name = ""
            m = _CLASS_RE.search(content)
            if m:
                class_name = m.group(1)
            if class_name.endswith("Test") or class_name.endswith("Tests"):
                continue
            files.append(JavaFile(path=path, content=content, package=package, class_name=class_name))
            count += 1
            if self._on_progress is not None and count % 500 == 0:
                self._on_progress(count)
        return files

    def all_files(self):
        return self._files

    def find_by_class_name(self, name):
        return self._by_name.get(name)

    def find_implementers(self, interface_name):
        return self._implements.get(interface_name, [])

    def find_by_simple_name(self, name):
        return [f for f in self._files if f.class_name == name]

    def internal_prefixes(self):
        packages = [f.package for f in self._files if f.package]
        if packages:
            prefix = _common_package_prefix(packages)
            if prefix:
                return [prefix]
        root_pom = self.project_dir / "pom.xml"
        poms = [root_pom] if root_pom.exists() else list(self.project_dir.rglob("pom.xml"))
        prefixes = []
        for pom in poms:
            text = pom.read_text(encoding="utf-8", errors="replace")
            g = self._own_group_id(text) or self._parent_group_id(text)
            if g and g not in _FRAMEWORK_GROUPS and g not in prefixes:
                prefixes.append(g)
        return prefixes

    @staticmethod
    def _own_group_id(text):
        stripped = re.sub(r"<parent>.*?</parent>", "", text, flags=re.DOTALL)
        stripped = re.sub(r"<dependencies>.*?</dependencies>", "", stripped, flags=re.DOTALL)
        stripped = re.sub(r"<dependencyManagement>.*?</dependencyManagement>", "", stripped, flags=re.DOTALL)
        stripped = re.sub(r"<build>.*?</build>", "", stripped, flags=re.DOTALL)
        m = re.search(r"<groupId>([^<]+)</groupId>", stripped)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _parent_group_id(text):
        m = re.search(r"<parent>.*?</parent>", text, flags=re.DOTALL)
        if not m:
            return ""
        gm = re.search(r"<groupId>([^<]+)</groupId>", m.group(0))
        return gm.group(1).strip() if gm else ""

    def yml_properties(self):
        props = {}
        for yml in list(self.project_dir.rglob("application.yml")) + list(
            self.project_dir.rglob("application.yaml")
        ):
            self._flatten_yml(yml.read_text(encoding="utf-8", errors="replace"), props)
        return props

    @staticmethod
    def _flatten_yml(text, props):
        stack = []
        for raw in text.splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            if "\t" in raw[:indent]:
                continue
            if ":" not in stripped:
                continue
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            level = indent // 2
            while len(stack) > level:
                stack.pop()
            if len(stack) == level:
                stack.append(key)
            else:
                stack = stack[:level] + [key]
            full = ".".join(stack)
            if val:
                props[full] = val
