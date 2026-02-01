def top_n_by_total_degree(indeg, outdeg, n):
    items = []
    for k in set(list(indeg.keys()) + list(outdeg.keys())):
        items.append((k, indeg.get(k, 0), outdeg.get(k, 0), indeg.get(k, 0) + outdeg.get(k, 0)))
    items.sort(key=lambda x: x[3], reverse=True)
    return items[:n]

def detect_dependency_magnets(indeg, outdeg, files_by_pkg, top_n):
    magnets = []
    tops = top_n_by_total_degree(indeg, outdeg, top_n)
    for (pkg, fin, fout, total) in tops:
        sample_files = []
        if pkg in files_by_pkg:
            # pick up to 3 largest files as "evidence"
            xs = sorted(files_by_pkg[pkg], key=lambda x: x.loc, reverse=True)
            i = 0
            while i < len(xs) and i < 3:
                sample_files.append(xs[i].rel_path + " (loc=" + str(xs[i].loc) + ")")
                i += 1
        magnets.append({
            "kind": "dependency_magnet",
            "package": pkg,
            "fan_in": fin,
            "fan_out": fout,
            "total_degree": total,
            "sample_files": sample_files
        })
    return magnets

def detect_cycles(cycles):
    out = []
    for c in cycles:
        out.append({"kind": "cycle", "cycle": c})
    return out

def detect_oversized_packages(files_by_pkg, top_n):
    items = []
    for pkg in files_by_pkg:
        total = 0
        for f in files_by_pkg[pkg]:
            total += f.loc
        items.append((pkg, total))
    items.sort(key=lambda x: x[1], reverse=True)

    out = []
    i = 0
    while i < len(items) and i < top_n:
        pkg, loc = items[i]
        out.append({"kind": "oversized_package", "package": pkg, "total_loc": loc})
        i += 1
    return out
