import sys

from tools.runtime import get_repo_path, get_collection
from rag_pipeline.qa_agent import run_question_answering

from arch.arch_agent import run_architecture_analysis
from arch.report import write_report


def run_qa(question, build_index, rebuild_index):
    answer = run_question_answering(question, build_index, rebuild_index)
    if answer is None:
        return
    print(answer)


def run_arch():
    repo_path = get_repo_path()
    if repo_path is None:
        return

    answer = run_architecture_analysis(repo_path)
    print(answer)
    write_report("out", answer)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py build [--rebuild]")
        print('  python main.py qa [--build|--rebuild] <question...>')
        print("  python main.py arch [--build|--rebuild]")
        print("")
        print("Repo path comes from rag_pipeline/config.py: REPO_PATH")
        return

    mode = sys.argv[1].strip()
    args = sys.argv[2:]

    build_index = False
    rebuild_index = False

    while args and args[0].startswith("--"):
        flag = args[0].strip()
        args = args[1:]
        if flag == "--build":
            build_index = True
        elif flag == "--rebuild":
            rebuild_index = True
        else:
            print("Unknown flag:", flag)
            return

    if mode == "build":
        _ = get_collection(build=True, rebuild=rebuild_index)
        return

    if mode == "qa":
        if not args:
            print("Need a question.")
            return
        question = " ".join(args).strip()
        run_qa(question, build_index=build_index, rebuild_index=rebuild_index)
        return

    if mode == "arch":
        run_arch()
        return

    print("Unknown mode:", mode)


if __name__ == "__main__":
    main()