import os
from tqdm import tqdm

from src.Utils import Performance_Evaluator
from src.Utils.IO import JSON_File_IO

def calculate_accuracy_at_k(bug_data):
    for top in [1,5,10]:
        count = 0
        total_bug = 0
        for bug in bug_data:
            suspicious_files = bug['suspicious_files']
            # length_of_suspicious_files = len(suspicious_files)

            fixed_files = bug['fixed_files']

            # fixed_files = bug['fixed_files'].split('.java')
            # fixed_files = [(file + '.java').strip() for file in fixed_files[:-1]]

            # print(bug['bug_id'], fixed_files)
            for fixed_file in fixed_files:
                if fixed_file in suspicious_files[0:top]:
                    # print(bug['bug_id'],fixed_file)
                    count = count + 1
                    break
            total_bug = total_bug + 1
        print('accuracy@', top, count, total_bug, (count*100/total_bug))


def calculate_mean_reciprocal_rank_at_k(bug_data):
    for top in [10]:
        total_bug = 0
        inverse_rank = 0
        for bug in bug_data:
            suspicious_files = bug['suspicious_files']
            length_of_suspicious_files = len(suspicious_files)
            fixed_files = bug['fixed_files']

            # fixed_files = bug['fixed_files'].split('.java')
            # fixed_files = [(file + '.java').strip() for file in fixed_files[:-1]]
            # print("ID ",item['bug_id'])
            # print(suspicious_files)
            # print("length_of_suspicious_files",length_of_suspicious_files)
            minimum_length = min(top,length_of_suspicious_files)
            for i in range(minimum_length):
                if(suspicious_files[i] in fixed_files):
                    # print('first rank', item['bug_id'], i+1, suspicious_files[i])
                    inverse_rank = inverse_rank + (1/(i+1))
                    break
            total_bug = total_bug + 1
        if inverse_rank == 0:
            print("MRR@", top, 0)
        else:
            print("MRR@", top, (1/total_bug)*inverse_rank, total_bug)
           
     
def calculate_mean_average_precision_at_k(bug_data):
    for top in [10]:
        total_bug = 0
        total_average_precision = 0
        for bug in bug_data:
            total_bug = total_bug + 1
            average_precision = 0
            precision = 0
            suspicious_files = bug['suspicious_files']
            length_of_suspicious_files = len(suspicious_files)
            fixed_files = bug['fixed_files']

            if not fixed_files:
                continue
            # fixed_files = bug['fixed_files'].split('.java')
            # fixed_files = [(file + '.java').strip() for file in fixed_files[:-1]]
            number_of_relevant_files = 0
            minimum_length = min(top,length_of_suspicious_files)
            for i in range(minimum_length):
                # print("i",i)
                if(suspicious_files[i] in fixed_files):
                    # print(item['bug_id'],suspicious_files[i], " relevant")
                    number_of_relevant_files = number_of_relevant_files + 1                        
                    precision = precision + (number_of_relevant_files/(i+1))
                # print("precision ", precision)
            average_precision = precision/len(fixed_files)
            # print("average_precision" ,average_precision, len(fixed_files))
            total_average_precision = total_average_precision + average_precision
            
        mean_average_precision = total_average_precision/total_bug
        print("MAP@", top, mean_average_precision, total_bug)

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
    projects_to_files = get_sorted_cache_files(base_dir="Output2/Cache")
    json_bugs = []
    for project, file_list in projects_to_files.items():
        for json_path in file_list:
            project_wise_json_bugs = JSON_File_IO.load_JSON_to_Dict(json_path)
            json_bugs.extend(project_wise_json_bugs)

    bug_data = []

    for bug in tqdm(json_bugs, desc="Processing JSON Bugs"):
        bug_id = bug['bug_id']
        project = bug['project']
        
        fixed_files = bug.get('fixed_files', []) or []
        es_results = bug.get('es_results', []) or []

        suspicious_files = []

        for result in es_results[:10]:
            file_url = result['file_url']
            suspicious_files.append(file_url)

        bug_data_entry = {
            'bug_id': f"{project}-{bug_id}",
            'fixed_files': fixed_files,
            'suspicious_files': suspicious_files
        }
        bug_data.append(bug_data_entry)

    calculate_accuracy_at_k(bug_data)
    calculate_mean_reciprocal_rank_at_k(bug_data)
    calculate_mean_average_precision_at_k(bug_data)