import os
import sys

def count_java_loc(repo_path):
    total = 0
    file_count = 0

    for root, _, files in os.walk(repo_path):
        for name in files:
            if not name.endswith(".java"):
                continue

            file_path = os.path.join(root, name)
            try:
                f = open(file_path, "r", encoding="utf-8", errors="ignore")
                text = f.read()
                f.close()
            except Exception:
                continue

            loc = 0
            for line in text.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith("//"):
                    continue
                loc += 1

            total += loc
            file_count += 1

    return total, file_count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/loc.py <repo_path>")
        sys.exit(1)

    repo_path = sys.argv[1].strip()
    total, n = count_java_loc(repo_path)
    print("repo_path=" + repo_path)
    print("java_files=" + str(n))
    print("total_loc=" + str(total))