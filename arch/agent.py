
import config
from arch.java_static import scan_repo_java
from arch.dep_graph import build_package_graph, compute_degrees, find_cycles
from tools.prompt_builder import build_architecture_prompt
from arch.smells import detect_dependency_magnets, detect_cycles, detect_oversized_packages
from rag_pipeline.llm_client import generate_answer
from arch.verify_arch import verify_arch_response  

def run_architecture_analysis(repo_path):
    java_files = scan_repo_java(repo_path)
    graph, files_by_pkg = build_package_graph(java_files)
    indeg, outdeg = compute_degrees(graph)

    cycle_lists = find_cycles(graph, limit=5)
    cycle_findings = detect_cycles(cycle_lists)

    magnets = detect_dependency_magnets(indeg, outdeg, files_by_pkg, top_n=5)
    oversized = detect_oversized_packages(files_by_pkg, top_n=5)

    evidence = _format_dependency_evidence(graph, cycle_findings, magnets, oversized)

    prompt = build_architecture_prompt(config.ARCH_QUERY, evidence)
    print("\n=== PROMPT ===\n")
    print(prompt)
    answer = generate_answer(prompt)

    ok2, msg = verify_arch_response(answer, evidence)
    if not ok2:
        return "BLOCKED: " + msg
    
    return answer





import re



def _format_dependency_evidence(graph, cycle_findings, magnets, oversized):
    """
    Evidence blob with stable IDs:
      - CYCLE_k lines
      - EDGE_k lines (derived from cycles)
      - MAGNET_k lines (with sample file paths as raw strings)
      - OVERSIZED_k lines

    No FILE index to keep prompt short for small context models.
    """
    n_nodes = len(graph.keys())
    n_edges = 0
    for k in graph:
        n_edges += len(graph[k])

    evidence_lines = []
    evidence_lines.append("Dependency evidence summary:")
    evidence_lines.append("SUMMARY: packages=" + str(n_nodes) + " edges=" + str(n_edges))

    # magnets
    evidence_lines.append("")
    evidence_lines.append("Dependency magnets (fan_in/fan_out/total):")
    if magnets:
        i = 0
        while i < len(magnets):
            m = magnets[i]
            mid = "MAGNET_" + str(i + 1)

            pkg = m.get("package")
            fin = m.get("fan_in")
            fout = m.get("fan_out")
            total = m.get("total_degree")

            evidence_lines.append(
                mid + ": " + str(pkg) + " fin=" + str(fin) + " fout=" + str(fout) + " total=" + str(total)
            )

            sample_files = m.get("sample_files") or []
            if sample_files:
                evidence_lines.append(mid + "_FILES: " + ", ".join(sample_files))
            i += 1
    else:
        evidence_lines.append("(none)")

    # cycles + edges
    evidence_lines.append("")
    evidence_lines.append("Cycles (package-level):")
    edge_id = 1
    if cycle_findings:
        c = 0
        while c < len(cycle_findings):
            cyc = cycle_findings[c].get("cycle", [])
            cid = "CYCLE_" + str(c + 1)

            evidence_lines.append(cid + ": " + " -> ".join(cyc))

            e = 0
            while e + 1 < len(cyc):
                a = cyc[e]
                b = cyc[e + 1]
                eid = "EDGE_" + str(edge_id)
                evidence_lines.append(eid + ": " + a + " -> " + b + " cycle=" + cid)
                edge_id += 1
                e += 1

            c += 1
    else:
        evidence_lines.append("(none)")

    # oversized
    evidence_lines.append("")
    evidence_lines.append("Oversized packages (by total LOC):")
    if oversized:
        k = 0
        while k < len(oversized):
            oid = "OVERSIZED_" + str(k + 1)
            pkg = oversized[k].get("package")
            loc = oversized[k].get("total_loc")
            evidence_lines.append(oid + ": " + str(pkg) + " total_loc=" + str(loc))
            k += 1
    else:
        evidence_lines.append("(none)")

    return "\n".join(evidence_lines)