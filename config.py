# config.py

# Repository root (edit this once)
REPO_PATH = "E:\\arch_task\\zip4j" 

# Chroma / embedding
EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"
CHROMA_COLLECTION_NAME = "zip4j_docs"
CHROMA_PERSIST_DIR = "./chroma_db"
CHROMA_SPACE = "cosine"

# Retrieval
TOP_K = 3
MAX_CANDIDATE_TOKENS = 1200
RETRIEVAL_SCOPE = "code"

# LM Studio (OpenAI-compatible)
LM_STUDIO_BASE_URL = "http://localhost:1234"
LM_STUDIO_MODEL = "qwen/qwen3-coder-30b"
LM_TEMPERATURE = 0
LM_TOP_P = 1.0
LM_TIMEOUT_SECS = 120

# Architecture analysis
ARCH_QUERY = (
        "Based on the dependency evidence, identify ONE architectural smell and propose ONE concrete refactoring.\n"
        "\n"
        "HARD CONSTRAINTS (must follow):\n"
        "1) Use ONLY the provided Context blocks. Do not assume any classes/files not shown.\n"
        "2) Pick ONE cycle from the evidence. Quote the cycle path EXACTLY as shown (e.g., `A -> B -> A`) and cite it.\n"
        "3) Name the exact dependency edge you will break, in the form: `Break edge: EDGE_k (<PkgA> -> <PkgB>)` and cite it.\n"
        "4) The 'Break edge' MUST be one of the arrows in the quoted cycle path (choose exactly one arrow from that path).\n"
        "5) Your 'Dependency rule (after)' must be consistent with your steps and rationale. If inconsistent, fix it.\n"
        "6) Evidence bullets must reference ONLY packages/classes that participate in the chosen smell (e.g., packages in the quoted cycle).\n"
        "   Do NOT cite unrelated packages (example: do not cite `tasks` LOC if the smell is `util <-> io.inputstream`).\n"
        "7) Steps MUST reference at least TWO EXISTING file paths that appear in EVIDENCE (verbatim). If you cannot, output the insufficient-evidence sentence.\n"
        "8) Steps must be non-overlapping and minimal: do NOT propose both moving an existing utility class and also creating a new utility wrapper\n"
        "   unless you explain why both are necessary. Prefer the smallest change that breaks the named edge.\n"
        "9) If an existing class is large (high LOC in context), prefer extracting only the needed methods into a smaller new class/package\n"
        "   instead of moving the whole class.\n"
        "10) Avoid moving core domain classes across packages. Prefer extracting a minimal subset (helper/interface) into a neutral package and keep the domain class in place.\n"
        "11) Steps must include at least one explicit 'extract' action (not only 'move').\n"
        "12) Do NOT invent method names. Only name a method (e.g., `readBytes`) if it appears verbatim in the Context; otherwise say\n"
        "    'extract the subset of methods used by <Class>'.\n"
        "13) If you introduce anything new (package/interface/class), label it as [NEW] and describe who will depend on it.\n"
        "14) Avoid vague statements like 'add a service layer' or 'introduce abstraction' unless you also provide:\n"
        "   - [NEW] names (package + interface/class),\n"
        "   - which existing classes will be edited to use it.\n"
        "15) Do NOT claim exact post-refactor fin/fout numbers unless they are explicitly computed in the Context.\n"
        "   Acceptance checks must be verifiable from the dependency graph (e.g., cycle disappears, forbidden imports removed).\n"
        "16) If the Context shows an oversized package is involved, your change must NOT worsen it by moving unrelated classes into it.\n"
        "\n"
        "ADDITIONAL CHECKABILITY RULES:\n"
        "A) Produce EXACTLY ONE complete response (no duplicate sections, no draft alternatives).\n"
        "B) In Evidence bullets, reference evidence IDs from Context (e.g., CYCLE_1 / MAGNET_1 / OVERSIZED_1).\n"
        "C) The Break edge line MUST reference exactly one EDGE_k ID from Context (e.g., EDGE_3).\n"
        "D) If you reference any file, you MUST copy its path verbatim from the Context from a *_FILES line (e.g., from a MAGNET_k_FILES line).\n"
        "E) If you mention any new package/class/file not present in Context, you MUST put `[NEW]` immediately before that identifier (example: `[NEW] com.foo.Bar`). You must add [NEW] every time you mention it, even if you have mentioned it before. Do not put `[NEW]` elsewhere. \n"
        "\n"
        "OUTPUT FORMAT (exact headings):\n"
        "Smell:\n"
        "- <name> \n"
        "\n"
        "Evidence:\n"
        "- <bullet 1: CYCLE_k: include exact cycle path copied verbatim> \n"
        "- <bullet 2: include one fin/fout/total line OR total_loc line copied verbatim (must be from cycle participants)>\n"
        "- <bullet 3: list 2 involved files by full path> \n"
        "\n"
        "Refactoring:\n"
        "- Break edge: EDGE_k (<PkgA> -> <PkgB>) \n"
        "- Dependency rule (after): <forbidden/allowed dependency directions using exact package names>\n"
        "- Change: <one sentence that mentions BOTH the broken edge AND the concrete mechanism (must include the word 'extract')>\n"
        "- Steps (3-6, imperative, each mentions a cited existing file path):\n"
        "  1) <edit file path ...; what exactly is extracted and where it goes> \n"
        "  2) <edit file path ...; update usage/imports to the extracted artifact> \n"
        "  3) Add [NEW] <package/interface/class name>; <who uses it> \n"
        "- Rationale: <explain how the steps remove the named edge and break the quoted cycle; no contradictions>\n"
        "- Expected impact:\n"
        "  - Maintainability: <...> \n"
        "  - Testability: <...> \n"
        "  - Evolvability: <...> \n"
        "  - Acceptance checks (verifiable, no guessed numbers):\n"
        "    - <cycle `...` disappears> \n"
        "    - <no imports from PkgA to PkgB remain> \n"
        "\n"
        "Trade-offs / Risks:\n"
        "- <1-3 bullets; must include one concrete risk such as API churn or refactor bug risk>\n"
        "\n"
        "Self-check:\n"
        "- Consistency: 'Dependency rule' matches 'Break edge' and all Steps.\n"
        "- Evidence coverage: Every file path referenced appears in Context.\n"
    )