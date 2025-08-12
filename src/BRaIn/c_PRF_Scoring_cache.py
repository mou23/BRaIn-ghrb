import hashlib
import os
import json
from tqdm import tqdm
from scipy.special import softmax

from src.IR import Searcher
from src.IR_Reretrieval.Searcher import Searcher_RE
from src.Utils import Performance_Evaluator
from src.Utils.IO import JSON_File_IO
from src.BRaIn.TextRank_KW_Search import TextRank

# Initialize TextRank
textRank = TextRank()


def re_search(bug_id, bug_title, bug_description, top_keywords, project, buggy_commit, responses=None,
              top_k=50):
    """Search and rerank the results based on the bug description and title."""
    url_score_dict = {}

    # Initialize the searcher
    searcher = Searcher_RE()

    # Perform the search
    score_dict = searcher.search_Extended(
        bug_id=bug_id,
        query=f"{bug_title} . {bug_description} . {top_keywords}",
        project=project,
        buggy_commit=buggy_commit,
        top_K_results=top_k,
        field_to_return=['file_url']
    )

    # Create a dictionary of file URLs and their BM25 scores
    for temp_dict in score_dict:
        file_url = temp_dict['file_url']
        bm25_score = temp_dict['bm25_score']
        url_score_dict[file_url] = bm25_score

    return url_score_dict


def get_all_scored_json_files(base_path="Output/Intelligent_Feedback"):
    """
    Collect all Scored_Cache_*.json files for each project.
    Returns a dict: { project_name: [file1, file2, ...] }
    """
    project_files = {}
    for project_name in os.listdir(base_path):
        project_dir = os.path.join(base_path, project_name)
        if os.path.isdir(project_dir):
            scored_files = [f for f in os.listdir(project_dir) if f.startswith("Scored_Cache") and f.endswith(".json")]
            if scored_files:
                project_files[project_name] = [os.path.join(project_dir, f) for f in scored_files]
    return project_files


if __name__ == '__main__':
    with_test = True
    all_project_files = get_all_scored_json_files()

    for project, json_files in all_project_files.items():
        print(f"\n--- Processing Project: {project} ---")

        refined_bugs_all = []

        for json_path in json_files:
            print(f"Processing: {json_path}")
            json_bugs = JSON_File_IO.load_JSON_to_Dict(json_path)

            for bug in tqdm(json_bugs, desc=f"Processing Bugs in {os.path.basename(json_path)}"):
                bug_id = bug['bug_id']
                bug_title = bug['bug_title']
                bug_description = bug['bug_description']
                project_name = bug['project']
                buggy_commit = bug['buggy_commit']
                responses = None

                ground_truths = bug['fixed_files']
                es_results = bug['es_results']
                documents = []
                track_results = []
                continued_score = []
                bm25_scores = []

                source_searcher = Searcher()

                for result in es_results:
                    methods = result.get('methods', {})
                    for method in methods:
                        if methods[method] == 'yes':
                            file_url = result['file_url']
                            sr = source_searcher.search_field(
                                project=project_name,
                                buggy_commit=buggy_commit,
                                field_to_search=file_url,
                                field_to_return=['source_code'],
                                top_K_results=1
                            )
                            try:
                                code_content = sr[0]['source_code']
                                documents.append(code_content)
                                break
                            except:
                                print(f"Error in getting source code for: {file_url}")
                                continue

                top_keywords = ''
                if documents:
                    query = f"{bug_title} . {bug_description}"
                    top_keywords = textRank.get_keywords_CodeRank(query, documents, no_of_keywords=20, window_size=15)
                    top_keywords = ' '.join(top_keywords)

                score_dict_re = re_search(bug_id, bug_title, bug_description, top_keywords, project_name, buggy_commit, responses)

                for result in es_results:
                    file_url = result['file_url']
                    track_results.append(file_url)
                    bm25_score = result['bm25_score']
                    bm25_scores.append(bm25_score)

                    methods = result.get('methods', {})
                    yes = any(methods[method] == 'yes' for method in methods)
                    continued_score.append(1 if yes else 0.0)

                score_dict_re = {k: v for k, v in score_dict_re.items() if k in track_results}

                try:
                    bm25_re_scores = softmax(list(score_dict_re.values()))
                    score_dict_re = dict(zip(score_dict_re.keys(), bm25_re_scores))
                except Exception as e:
                    print("Error in softmax:", e)
                    continue

                # Softmax over original BM25 scores with LLM weighting
                scores = softmax(bm25_scores)
                score_dict = {}
                for index, file in enumerate(track_results):
                    score_dict[file] = scores[index] * continued_score[index]

                sorted_score_dict = dict(sorted(score_dict.items(), key=lambda item: item[1], reverse=True))
                search_results = list(sorted_score_dict.keys())

                if not with_test:
                    ground_truths = [file for file in ground_truths if 'test' not in file.split('.')[-2].lower()]
                bug['fixed_files'] = ground_truths

                # Update ES results
                for result in es_results:
                    file_url = result['file_url']
                    result['bm25_score'] = sorted_score_dict.get(file_url, 0)

                bug['es_results'] = sorted(es_results, key=lambda x: x['bm25_score'], reverse=True)
                refined_bugs_all.append(bug)

        # Save refined results for the project
        save_dir = os.path.join("Output", "Cache", project)
        os.makedirs(save_dir, exist_ok=True)
        save_file = os.path.join(save_dir, "Mistral_ZERO_sorted_cache.json")
        JSON_File_IO.save_Dict_to_JSON(refined_bugs_all, save_dir, "Mistral_ZERO_sorted_cache.json", with_indent=True)
        print(f"Saved refined results for {project} at: {save_file}")