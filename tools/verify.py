import re

CITE_RE = re.compile(r"\[C(\d+)\]")

EVIDENCE_ID_RE = re.compile(r"\b(CYCLE_\d+|EDGE_\d+|MAGNET_\d+|OVERSIZED_\d+)\b")
EDGE_LINE_RE = re.compile(r"^\s*EDGE_\d+:\s*(.+?)\s*cycle=CYCLE_\d+\s*$")
MAGNET_LINE_RE = re.compile(r"^\s*MAGNET_\d+:\s*([a-zA-Z0-9_.]+)\s+fin=")
OVERSIZED_LINE_RE = re.compile(r"^\s*OVERSIZED_\d+:\s*([a-zA-Z0-9_.]+)\s+total_loc=")

BREAK_EDGE_LINE_RE = re.compile(r"^\s*-\s*Break edge:\s*(.*)$", re.IGNORECASE)
EDGE_ID_IN_TEXT_RE = re.compile(r"\bEDGE_\d+\b")
CYCLE_ID_IN_TEXT_RE = re.compile(r"\bCYCLE_\d+\b")

PKG_TOKEN_RE = re.compile(r"net\.lingala\.zip4j(?:\.[A-Za-z0-9_]+)+")
NEW_MARK_RE = re.compile(r"\[NEW\]")


def verify_citations(answer_text, num_contexts):
    if not answer_text:
        return False, "Empty answer."

    matches = CITE_RE.findall(answer_text)
    if not matches:
        return False, "No citations found. Expected [C1], [C2], ..."

    i = 0
    while i < len(matches):
        n = int(matches[i])
        if n < 1 or n > num_contexts:
            return False, "Citation [C" + str(n) + "] is out of range."
        i += 1

    return True, ""


def _count_heading(answer_text, heading):
    return answer_text.count("\n" + heading + "\n") + (1 if answer_text.startswith(heading + "\n") else 0)


def _collect_valid_ids(evidence_text):
    ids = set()
    for line in evidence_text.splitlines():
        for x in EVIDENCE_ID_RE.findall(line):
            ids.add(x)
    return ids


def _collect_allowed_packages(evidence_text):
    """
    Allowed packages = packages appearing in:
      - CYCLE lines (via EDGE arrows)
      - EDGE lines (A -> B)
      - MAGNET lines (pkg)
      - OVERSIZED lines (pkg)
    """
    allowed = set()

    for line in evidence_text.splitlines():
        line = line.strip()

        # EDGE_k: A -> B cycle=CYCLE_1
        m = EDGE_LINE_RE.match(line)
        if m:
            arrow = m.group(1).strip()
            parts = arrow.split("->")
            if len(parts) == 2:
                a = parts[0].strip()
                b = parts[1].strip()
                allowed.add(a)
                allowed.add(b)
            continue

        m = MAGNET_LINE_RE.match(line)
        if m:
            allowed.add(m.group(1).strip())
            continue

        m = OVERSIZED_LINE_RE.match(line)
        if m:
            allowed.add(m.group(1).strip())
            continue

    return allowed


def verify_arch_response(answer_text, evidence_text):
    """
    checks:
      1) Must be single response (headings appear once)
      2) Evidence section must reference a CYCLE_k
      3) Break edge must reference exactly one EDGE_k that exists
      4) Any package token mentioned must be in allowed packages OR line includes [NEW]
    """

    for h in ["Smell:", "Evidence:", "Refactoring:", "Trade-offs / Risks:", "Self-check:"]:
        if _count_heading(answer_text, h) != 1:
            return False, "Duplicate or missing heading: " + h

    valid_ids = _collect_valid_ids(evidence_text)
    allowed_pkgs = _collect_allowed_packages(evidence_text)

    # must reference a CYCLE_k somewhere in Evidence section
    if "Evidence:" in answer_text:
        ev_part = answer_text.split("Evidence:", 1)[1]
        if "Refactoring:" in ev_part:
            ev_part = ev_part.split("Refactoring:", 1)[0]
        if not CYCLE_ID_IN_TEXT_RE.search(ev_part):
            return False, "Evidence must reference one CYCLE_k ID from Context."
        # also ensure any referenced IDs exist
        for x in EVIDENCE_ID_RE.findall(ev_part):
            if x not in valid_ids:
                return False, "Evidence references unknown ID: " + x

    # Break edge must reference exactly one EDGE_k id
    ref_part = answer_text.split("Refactoring:", 1)[1] if "Refactoring:" in answer_text else ""
    lines = ref_part.splitlines()

    break_line = None
    for line in lines:
        m = BREAK_EDGE_LINE_RE.match(line.strip())
        if m:
            break_line = line
            break

    if break_line is None:
        return False, "Missing '- Break edge:' line."

    edge_ids = EDGE_ID_IN_TEXT_RE.findall(break_line)
    if len(edge_ids) != 1:
        return False, "Break edge must reference exactly one EDGE_k ID."

    if edge_ids[0] not in valid_ids:
        return False, "Break edge references unknown EDGE id: " + edge_ids[0]

    # package tokens must be allowed or marked [NEW] on same line
    seen_new = set()
    for line in answer_text.splitlines(): 
        is_new = NEW_MARK_RE.search(line) is not None 
        pkgs = PKG_TOKEN_RE.findall(line) 
        for p in pkgs:
            if (p not in allowed_pkgs) and (not is_new) and (p not in seen_new): 
                return False, "Unknown package not in Context (mark [NEW] if intended): " + p
            seen_new.add(p)
    return True, "OK"