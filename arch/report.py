import os

def write_report(out_dir, text):
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    path = os.path.join(out_dir, "part_b_report.md")
    f = open(path, "w", encoding="utf-8")
    f.write(text)
    f.close()
    print("Wrote:", path)