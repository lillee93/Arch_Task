def _best_internal_package(import_path, internal_packages):
    # Map "a.b.c.Class" to the longest matching known package prefix.
    best = ""
    for pkg in internal_packages:
        if import_path == pkg or import_path.startswith(pkg + "."):
            if len(pkg) > len(best):
                best = pkg
    return best

def build_package_graph(java_files):
    internal_packages = set()
    for f in java_files:
        if f.package:
            internal_packages.add(f.package)

    graph = {}
    files_by_pkg = {}

    for f in java_files:
        if f.package not in graph:
            graph[f.package] = set()
        if f.package not in files_by_pkg:
            files_by_pkg[f.package] = []
        files_by_pkg[f.package].append(f)

    for f in java_files:
        src_pkg = f.package
        if not src_pkg:
            continue

        for imp in f.imports:
            dst_pkg = _best_internal_package(imp, internal_packages)
            if not dst_pkg:
                continue
            if dst_pkg == src_pkg:
                continue
            graph[src_pkg].add(dst_pkg)

    return graph, files_by_pkg

def compute_degrees(graph):
    indeg = {}
    outdeg = {}
    for a in graph:
        outdeg[a] = len(graph[a])
        if a not in indeg:
            indeg[a] = 0
        for b in graph[a]:
            indeg[b] = indeg.get(b, 0) + 1
            if b not in outdeg:
                outdeg[b] = outdeg.get(b, 0)
    return indeg, outdeg

def find_cycles(graph, limit):
    cycles = []
    visited = set()
    stack = []
    on_stack = set()

    def dfs(u):
        if len(cycles) >= limit:
            return
        visited.add(u)
        stack.append(u)
        on_stack.add(u)

        for v in graph.get(u, []):
            if v not in visited:
                dfs(v)
            elif v in on_stack:
                i = 0
                while i < len(stack):
                    if stack[i] == v:
                        cycle = stack[i:] + [v]
                        cycles.append(cycle)
                        break
                    i += 1
                if len(cycles) >= limit:
                    break

        on_stack.remove(u)
        stack.pop()

    for n in graph:
        if n not in visited:
            dfs(n)
        if len(cycles) >= limit:
            break

    return cycles
