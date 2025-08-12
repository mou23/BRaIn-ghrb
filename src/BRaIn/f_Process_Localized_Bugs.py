import os
import csv
from tqdm import tqdm

from src.Utils import Performance_Evaluator
from src.Utils.IO import JSON_File_IO


def check_localization_at_k(fixed_files, suspicious_files, k):
    """Return True if any fixed file is in the top-k suspicious files."""
    top_files = suspicious_files[:k]
    for fixed_file in fixed_files:
        if fixed_file in top_files:
            return True
    return False


def get_sorted_cache_files(base_dir="Output/Cache"):
    """
    Returns { project_name: [sorted_cache_json_paths...] }
    Looks for 'Mistral_ZERO_sorted_cache.json' first; if missing, falls back to any '*_sorted_cache.json'.
    """
    project_files = {}
    if not os.path.isdir(base_dir):
        print(f"Base dir not found: {base_dir}")
        return project_files

    for project in os.listdir(base_dir):
        proj_dir = os.path.join(base_dir, project)
        if not os.path.isdir(proj_dir):
            continue

        preferred = os.path.join(proj_dir, "Mistral_ZERO_sorted_cache.json")
        files = []
        if os.path.isfile(preferred):
            files = [preferred]
        else:
            files = [
                os.path.join(proj_dir, f)
                for f in os.listdir(proj_dir)
                if f.endswith("_sorted_cache.json")
            ]
        if files:
            project_files[project] = files
    return project_files


if __name__ == '__main__':
    trial = "3"
    projects_to_files = get_sorted_cache_files(base_dir=f"Output{trial}/Cache")
    json_bugs = []
    for project, file_list in projects_to_files.items():
        for json_path in file_list:
            project_wise_json_bugs = JSON_File_IO.load_JSON_to_Dict(json_path)
            json_bugs.extend(project_wise_json_bugs)

    acc1_ids, acc5_ids, acc10_ids = [], [], []

    for bug in tqdm(json_bugs, desc="Processing JSON Bugs"):
        bug_id = f"{bug['project']}-{bug['bug_id']}"
        fixed_files = bug.get('fixed_files', []) or []
        es_results = bug.get('es_results', []) or []

        suspicious_files = [result['file_url'] for result in es_results[:10]]

        if check_localization_at_k(fixed_files, suspicious_files, 1):
            acc1_ids.append(bug_id)
        if check_localization_at_k(fixed_files, suspicious_files, 5):
            acc5_ids.append(bug_id)
        if check_localization_at_k(fixed_files, suspicious_files, 10):
            acc10_ids.append(bug_id)

    # Align rows so CSV has equal length columns (fill empty cells with "")
    max_len = max(len(acc1_ids), len(acc5_ids), len(acc10_ids))
    rows = []
    for i in range(max_len):
        rows.append([
            acc1_ids[i] if i < len(acc1_ids) else "",
            acc5_ids[i] if i < len(acc5_ids) else "",
            acc10_ids[i] if i < len(acc10_ids) else ""
        ])

    out_file = f"localized_bugs{trial}.csv"
    with open(out_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["accuracy@1", "accuracy@5", "accuracy@10"])
        writer.writerows(rows)

    print(f"Wrote bug IDs to {out_file}")
