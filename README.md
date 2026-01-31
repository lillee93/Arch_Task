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

#### Code: file-by-file chunking (one file = one chunk)

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
- results are reproducible for reviewers.

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

This is designed to prevent hallucination when retrieval misses key information.

#### Part B prompt (Architecture refactoring)

The architecture prompt is intentionally strict and checkable:

- Answer **ONLY** using the `EVIDENCE` block
- Reference evidence IDs exactly (e.g., `CYCLE_k`, `EDGE_k`, `MAGNET_k`, `OVERSIZED_k`)
- Copy file paths verbatim from `*_FILES` evidence lines
- Produce exactly one response following the required headings/format
- If evidence is insufficient, output exactly:  
  `I cannot propose a concrete refactoring from the provided evidence.`

The goal is to avoid generic architecture advice and force **system-specific, evidence-grounded** recommendations.

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

## Handling LLM Non-Determinism, Uncertainty, and Hallucination

This solution is designed so the LLM is **never the single source of truth**:

- **Deterministic settings:** `LM_TEMPERATURE = 0` (stable output).
- **Hard grounding constraints:**
  - Part A can only use retrieved Context blocks.
  - Part B can only use the computed EVIDENCE block and evidence IDs.
- **Fail-closed behavior:** prompts instruct the model to refuse with an exact sentence when evidence/context is insufficient.
- **Checkability:** architecture output requires explicit evidence IDs, explicit “break edge”, and file paths copied verbatim from evidence.

Known limitations:

- Import-based dependency graphs are approximations (reflection/dynamic wiring is not captured).
- RAG answers are bounded by retrieval quality; the prompt explicitly avoids guessing.

---

## Output Artifacts

Depending on enabled debug settings, the repo may output:

- Persistent Chroma DB directory: `./chroma_db/`
- Optional prompt/evidence dumps (useful for reviewer traceability)

---

## Notes

- Part A and Part B are intentionally decoupled:
  - Part A depends on the Chroma index.
  - Part B uses static dependency analysis only and does not need embeddings.

---
