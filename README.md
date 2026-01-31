# Arch_Task — Minimal RAG (Part A) + Architecture Agent (Part B) for Zip4j

This repository implements a lightweight, interview-assignment style solution for the “Software Architecture in the AI Era” work test:

- **Part A (Minimal RAG Prototype):** build a persistent index over a Java codebase and answer questions using retrieval + an LLM, with citations to retrieved context.
- **Part B (Architecture-Oriented Agent Workflow):** extract a package dependency graph via static analysis, detect architecture smells (cycles / dependency magnets / oversized packages), produce an **EVIDENCE** block, and ask an LLM to propose **ONE** concrete refactoring grounded strictly in that evidence.

---

## Repository Layout

- `main.py`  
  CLI entry point: `build`, `rebuild`, `qa`, `arch`.

- `config.py`  
  Central configuration (repo path, Chroma persistence path, model settings).

- `rag_pipeline/`  
  Part A: ingestion, chunking, embedding, retrieval, QA prompt building.

- `arch/`  
  Part B: static dependency extraction, graph build, smell detection, evidence formatting, architecture prompting/verification.

- `tools/`  
  Prompt builders and small utilities.

- `zip4j/`  
  Target Java repo snapshot for reproducibility (Zip4j).

---

## Environment Requirements

- **Python:** 3.11+
- **Vector store:** Chroma (persistent local store)
- **LLM runtime:** LM Studio (OpenAI-compatible server)
- **OS:** Windows 11 (tested), should also work on macOS/Linux with path adjustments

---

## Setup

### 1) Clone

```bash
git clone https://github.com/lillee93/Arch_Task.git
cd Arch_Task
```

### 2) Create a virtual environment

**Windows (PowerShell):**
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Start LM Studio

Start an OpenAI-compatible API server in LM Studio and keep it running. Default config assumes:

- Base URL: `http://localhost:1234`
- Model: `qwen/qwen3-coder-30b`

---

## Configuration (`config.py`)

Edit `config.py` to match your environment.

```python
# Repository root (edit this once)
REPO_PATH = "E:\\arch_task\\zip4j"

# Chroma / embedding
EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"
CHROMA_COLLECTION_NAME = "zip4j_docs"
CHROMA_PERSIST_DIR = "./chroma_db"
CHROMA_SPACE = "cosine"

# Retrieval
TOP_K = 3

# LM Studio (OpenAI-compatible)
LM_STUDIO_BASE_URL = "http://localhost:1234"
LM_STUDIO_MODEL = "qwen/qwen3-coder-30b"
LM_TEMPERATURE = 0
LM_TOP_P = 1.0
LM_TIMEOUT_SECS = 120

# Architecture analysis
ARCH_QUERY = "..."
```

Notes:

- **Part A requires building the Chroma index once** (`python main.py build`).
- **Part B does not require the index**; it runs directly from static dependency analysis.

---

## How to Run

Run all commands from the repo root.

### Part A — Minimal RAG QA

#### Step 1) Build the persistent index (required before QA)

```bash
python main.py build
```

This ingests the repo at `REPO_PATH`, chunks it, embeds it, and persists the Chroma collection under `CHROMA_PERSIST_DIR`.

#### Step 2) Ask a question

```bash
python main.py qa "Where is AES encryption implemented?"
```

What happens:

- The pipeline retrieves `TOP_K` chunks from Chroma.
- The LLM is prompted to answer **only** using retrieved context blocks.
- The answer includes citations like `[C1]`, `[C2]` that map back to the retrieved blocks.

#### Optional) Rebuild the index (when repo/config changed)

```bash
python main.py rebuild
```

Use `rebuild` if:

- you changed the target repo,
- you changed chunking strategy,
- you changed the embedding model,
- or you want to refresh embeddings after code changes.

---

### Part B — Architecture Analysis Agent (no index build needed)

```bash
python main.py arch
```

What it does:

1. Scans Java files and extracts `package` and `import` relations (static analysis).
2. Builds a **package dependency graph**.
3. Detects smells (at least one of):
   - **cyclic dependencies**
   - **dependency magnets** (fan-in/fan-out hotspots)
   - **oversized packages** (high total LOC)
4. Produces an **EVIDENCE** block (cycles/edges/magnets/oversized + file paths).
5. Prompts the LLM to propose **ONE** concrete refactoring grounded strictly in that evidence.

---

## Design Decisions (Chunking, Retrieval, Prompting, Dependency Analysis)

### Chunking Strategy

#### Code: file-by-file chunking 

I chunk Java code **file-by-file** to make retrieval more reliable under real constraints:

- **Reduced “missing context” risk under limited TOP_K and token budgets**  
  In code RAG, prompt size is limited. If code is split into many small fragments, answering often requires multiple fragments to appear in the top-k. Missing *one* fragment (e.g., helper methods, constants, local types) can make an answer incomplete. File chunks keep related context together, increasing the probability that one retrieved chunk contains what’s needed.

- **Less sensitivity to embedding/retrieval noise**  
  Smaller chunks are more brittle: ranking quality can vary with query phrasing and embedding behavior. File-level chunks provide stronger semantic signal (imports + class + helpers) and are less likely to “almost match” while missing the crucial lines.

- **Better provenance and reviewability**  
  Citations map cleanly to a file path (e.g., `src/.../Foo.java`), which makes results easy to verify.

Trade-off:

- File chunks can be large. I keep retrieval small (`TOP_K = 3`) and enforce strict grounding so the model refuses rather than guessing when context is insufficient.

#### Docs: paragraph chunking

Documentation is chunked by **paragraph** to preserve coherent natural-language units without mixing unrelated topics into a single chunk.

---

### Retrieval Strategy (Part A)

#### Chroma persistent vector store

I use **Chroma persistence** so:

- indexing is a one-time cost,
- repeated QA runs are fast,
- results are reproducible.

The CLI supports:

- `python main.py build` (create index once)
- `python main.py rebuild` (refresh index after changes)
- `python main.py qa ...` (query using the persisted index)

---

### Prompting & Grounding Strategy

I use two prompts because Part A and Part B have different failure modes.

#### Part A prompt (RAG QA)

The QA prompt enforces strict grounding:

- Answer **ONLY** using provided Context blocks
- Cite important statements using `[C1]`, `[C2]`, ...
- If context is insufficient, output:  
  `I cannot answer from the provided context.`

#### Part B prompt (Architecture refactoring)

The architecture prompt is intentionally strict and checkable:

- Answer **ONLY** using the `EVIDENCE` block
- Reference evidence IDs exactly (e.g., `CYCLE_k`, `EDGE_k`, `MAGNET_k`, `OVERSIZED_k`)
- Copy file paths verbatim from `*_FILES` evidence lines
- Produce exactly one response following the required headings/format
- If evidence is insufficient, output exactly:  
  `I cannot propose a concrete refactoring from the provided evidence.`

---

### Dependency Analysis Approach (Part B)

Part B uses lightweight static analysis (fast, reproducible, assignment-appropriate):

- Parse Java `package ...;` and `import ...;` from each `.java` file
- Exclude `src/test/` so test-only dependencies don’t skew the architecture view
- Build a directed **package dependency graph**:
  - nodes = packages
  - edges = “package A imports something from package B”
- Use “longest matching package prefix” to map imports like `a.b.c.Foo` to package `a.b.c` if present

#### Smell detection heuristics

- **Cycles:** detect cycles from the package graph and emit explicit cycle paths.
- **Dependency magnets:** compute fan-in/fan-out per package and rank hotspots; attach representative large files as evidence.
- **Oversized packages:** aggregate LOC per package and report the largest.

These heuristics are intentionally simple (no heavy parsing frameworks) to keep the solution minimal and runnable.

---

## Handling LLM Non-Determinism, Hallucination, and Post-Checks

This solution is designed so the LLM is **never the single source of truth**, and it **fails closed** (refuses / falls back / blocks) instead of inventing answers.

### 1) Hard grounding constraints (prompt-level)

Grounding starts in the prompts:

- **Part A:** “answer only using Context blocks” + mandatory `[Ck]` citations.
- **Part B:** “answer only using EVIDENCE” + mandatory evidence IDs (e.g., `CYCLE_1`, `EDGE_3`) + verbatim file paths.

This discourages the model from introducing facts that are not in retrieval/evidence.

### 2) Availability check (LM Studio)

Before calling the LLM, the code checks that the server/model is reachable by querying the OpenAI-compatible models endpoint:

- `GET {LM_STUDIO_BASE_URL}/v1/models` with a short timeout

If the LLM is down or unconfigured, the system uses fallback output.

### 3) Part A guardrails + post-check + fallback (QA)

**Guardrail A — retrieval relevance check**  
After retrieving top-k chunks, the pipeline checks whether the retrieval looks related to the question using a small token-overlap heuristic:

- tokenize question terms
- remove stop words
- count matches in each retrieved chunk
- require a minimal threshold (>= 2 matched terms somewhere in top-k)

If retrieval appears unrelated, the pipeline returns a safe fallback response.

**Guardrail B — safe fallback answer**  
If retrieval is unrelated, the LLM is unavailable, or the LLM call fails, the pipeline returns:

- `I cannot answer from the provided context.`
- a reason (e.g., “retrieval seems unrelated”, “LLM not available”, “LLM error…”)
- a list of retrieved sources with `[C1]..[Ck]` citations
- short evidence snippets around the best matching lines (so a reviewer can manually inspect)

**Post-check — verify citations before returning**  
Whether the answer comes from LLM **or** fallback, it is validated by a verifier:

- must contain at least one citation like `[C1]`
- each `[Ck]` must be within `1..num_contexts`

If verification fails, the pipeline returns a hard block message (`BLOCKED: <reason>`).

### 4) Part B post-check + fallback (Architecture)

Part B also uses fail-closed behavior with explicit verification:

- If the LLM is unavailable: return a minimal evidence-grounded fallback refactoring (or print raw evidence if no cycle/edge can be picked).
- If the LLM responds: validate output against strict, checkable constraints before accepting it.

**Post-check — structural + evidence validity**  
The architecture verifier checks, among other things:

- each required heading appears **exactly once**
- the Evidence section references a `CYCLE_k` and only uses IDs that exist in the EVIDENCE block
- the “Break edge” line references **exactly one** existing `EDGE_k`
- any Zip4j package tokens mentioned must appear in the allowed packages derived from EVIDENCE, otherwise the line must be marked `[NEW]`

If verification fails, the pipeline returns a fallback response with “verify failed: …” instead of accepting hallucinated output.

### Deterministic settings

Default model settings are conservative for repeatability:

- `LM_TEMPERATURE = 0`
- `LM_TOP_P = 1.0`
- `LM_TIMEOUT_SECS = 120`

---

## Output Artifacts

The repo may output:

- Persistent Chroma DB directory: `./chroma_db/`
- Recommendations for Architectural Improvement 'out/part_b_report.md'

---


## Limitations

### Part A (RAG QA)

- **File-level embedding has size + storage costs**  
  Embedding whole files increases index size and embedding time. For larger repositories, this can become expensive to store and slower to build/rebuild.

- **Large chunks can exceed LLM context limits**  
  Even when retrieval finds the “right” file, the chunk may be too large to fit into the LLM prompt alongside instructions and other retrieved blocks. This can force truncation or reduce the number of chunks that can be included, which may lower answer quality.

- **Granularity trade-off (file vs method)**  
  File chunks reduce “missing local context” risk, but they lose precision for pinpoint questions (e.g., one method) and increase the chance that the most relevant snippet is buried inside a large block.

- **Retrieval remains the bottleneck**  
  Answers are bounded by what is retrieved in `TOP_K`. If the correct file is not retrieved (or is retrieved but too large to include), the system is designed to refuse.

### Part B (Architecture Analysis)

- **Evidence-only: no method-level refactoring details**  
  Part B is grounded in **dependency evidence computed from the codebase** (imports/packages, fan-in/out, LOC, cycles). It does **not** pull detailed code context via the Part A RAG retrieval.  
  As a result, refactoring proposals are **structural and package-level**, not method-by-method transformations.

- **Static dependency approximation**  
  Import-based dependency graphs approximate architecture and may miss dynamic wiring.

- **Refactoring recommendations are constrained by evidence granularity**  
  Because the EVIDENCE block focuses on packages/edges/files (not full AST or call graphs), recommendations prioritize breaking dependency edges and improving modular boundaries, rather than proposing exact method signatures or precise extraction steps at the method level.
```

---
