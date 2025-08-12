import os
from tqdm import tqdm

from src.Utils import Performance_Evaluator
from src.Utils.IO import JSON_File_IO

def checkGTExists(fixed_files, results):
    for file in fixed_files:
        if file in results:
            print(f"Found GT: {file}")
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
    count_of_found_gt = 0
    projects_to_files = get_sorted_cache_files(base_dir="Output/Cache")
    json_bugs = []
    for project, file_list in projects_to_files.items():
        for json_path in file_list:
            project_wise_json_bugs = JSON_File_IO.load_JSON_to_Dict(json_path)
            json_bugs.extend(project_wise_json_bugs)

    all_ground_truths = []
    all_search_results = []

    for bug in tqdm(json_bugs, desc="Processing JSON Bugs"):
        bug_id = bug['bug_id']
        bug_title = bug['bug_title']
        bug_description = bug['bug_description']
        project = bug['project']
        buggy_commit = bug['buggy_commit']
        responses = None
        # responses = bug['response']

        ground_truths = bug['fixed_files']
        search_results = []

        es_results = bug['es_results']

        for result in es_results[:10]:
            file_url = result['file_url']

            search_results.append(file_url)

        all_ground_truths.append(ground_truths)
        all_search_results.append(search_results)

    gt_tracker_by_count = {}
    sr_tracker_by_count = {}
    for gt, sr in zip(all_ground_truths, all_search_results):

        if checkGTExists(gt, sr):
            count_of_found_gt += 1


        if len(gt) <= 3:
            if len(gt) in gt_tracker_by_count:
                gt_tracker_by_count[len(gt)].append(gt)
                sr_tracker_by_count[len(gt)].append(sr)
            else:
                gt_tracker_by_count[len(gt)] = [gt]
                sr_tracker_by_count[len(gt)] = [sr]
        else:
            if 4 in gt_tracker_by_count:
                gt_tracker_by_count[4].append(gt)
                sr_tracker_by_count[4].append(sr)
            else:
                gt_tracker_by_count[4] = [gt]
                sr_tracker_by_count[4] = [sr]
    # evaluate the search results

    refined_gt = []
    refined_sr = []
    for key, value in gt_tracker_by_count.items():
        performance_evaluator = Performance_Evaluator()
        search_results = sr_tracker_by_count[key]
        performance = performance_evaluator.evaluate_several(value, search_results, at_Ks=[1, 5, 10])

        refined_gt.extend(value)
        refined_sr.extend(search_results)

        print(f"GT Count: {key} GT files: {len(value)} Performance: {performance}")

    # evaluate the search results
    performance_evaluator = Performance_Evaluator()
    performance = performance_evaluator.evaluate_several(refined_gt, refined_sr, at_Ks=[1, 5, 10])

    print(f"Whole Performance: {performance} Refined Total Bug Reports: {len(refined_gt)}")
    print(f"Found Gt for {count_of_found_gt} bugs")
