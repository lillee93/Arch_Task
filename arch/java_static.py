# arch/java_static.py
import os
import re

PACKAGE_RE = re.compile(r"^\s*package\s+([a-zA-Z0-9_.]+)\s*;", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*import\s+([a-zA-Z0-9_.]+)\s*;", re.MULTILINE)

class JavaFileInfo:
    def __init__(self, rel_path, package, imports, loc):
        self.rel_path = rel_path
        self.package = package
        self.imports = imports
        self.loc = loc

def count_loc(text):
    loc = 0
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("//"):
            continue
        loc += 1
    return loc

def parse_java_file(abs_path, rel_path):
    try:
        f = open(abs_path, "r", encoding="utf-8", errors="ignore")
        text = f.read()
        f.close()
    except Exception:
        return None

    m = PACKAGE_RE.search(text)
    pkg = m.group(1) if m else ""

    imports = []
    for im in IMPORT_RE.findall(text):
        imports.append(im)

    loc = count_loc(text)
    return JavaFileInfo(rel_path.replace(os.sep, "/"), pkg, imports, loc)

def scan_repo_java(repo_path):
    out = []
    for root, _, files in os.walk(repo_path):
        for name in files:
            if not name.endswith(".java"):
                continue
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, repo_path).replace(os.sep, "/")

            # Always exclude tests
            if rel_path.startswith("src/test/"):
                continue

            info = parse_java_file(abs_path, rel_path)
            if info:
                out.append(info)
    return out
