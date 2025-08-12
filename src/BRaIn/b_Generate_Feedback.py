import json
import html
import os
import sys
from transformers import AutoTokenizer

from vllm import LLM, SamplingParams
from tqdm import tqdm
from src.Utils import JSON_File_IO
from transformers import AutoTokenizer


def load_dataframe(file_path):
    return JSON_File_IO.load_JSON_to_Dataframe(file_path)


def load_json_to_dict(file_path):
    return JSON_File_IO.load_JSON_to_Dict(file_path)


def llm_scoring(es_results, bug_title, bug_description, llm):
    tokenizer = AutoTokenizer.from_pretrained("marinarosell/Mistral-7B-Instruct-v0.3-GPTQ-8bit-gs128")

    user_role = {"role": "user", "content": ""}
    assistant_role = {"role": "assistant", "content": ""}

    user_text = """You are a helpful AI software engineer specializing in identifying buggy code segments given a bug report. Analyze the provided bug report and the JAVA code segment to determine if the code segment is responsible for causing the bug described in the bug report. You need to understand the functionality of the code segment and the details of the bug report to determine the relevance of the code segment to the bug report.

There are three possible outputs: 'yes', 'no', 'possible'.
-'yes': The code is responsible for the bug described in the bug report.
-'no': The code is NOT responsible for the bug described in the bug report.
-'possible': The code can be partially responsible for the bug described in the bug report.

Provide your output in JSON format like this sample: {"relevance": "yes"}.

Act like a rational software engineer and provide output. Avoid emotion and extra text other than JSON.

### 
Analyze the following bug report and code segment for relevance:"""

    instruction = '''Please determine if the code segment is responsible for the bug described in the bug report.'''

    bug_report = f'''Bug Report: \n- {bug_title} \n- {bug_description}'''

    for result in es_results:
        # file_url = result['file_url']
        # bm25_score = result['bm25_score']

        methods = result['methods']

        prompts = []

        # now, iterate over the key/value pairs of the methods in dictionary
        for method_name, method_body in methods.items():
            # add the method_body to the context

            code_context = f'''Code Segment: \n {method_body} '''

            # now, create the prompt
            prompt = user_text + '\n\n' + bug_report + '\n\n' + code_context + '\n\n' + instruction + '\n###'

            chat = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": ""},
            ]

            template = tokenizer.apply_chat_template(chat, tokenize=False)
            prompts.append(template)

        outputs = llm.generate(prompts)

        # zip through outputs and methods
        for output, method_name in zip(outputs, methods.keys()):
            # prompt = output.prompt
            response = output.outputs[0].text

            is_relevant = 'no'

            # check if the response contains 'yes', 'no'
            if 'yes' in response:
                is_relevant = 'yes'
            elif 'no' in response:
                is_relevant = 'no'

            # is_relevant = json.loads(response)['relevance']

            # add the score to the es_results
            result['methods'][method_name] = is_relevant

    return es_results

def get_projects_from_base_path(base_path):
    projects = {}
    for filename in os.listdir(base_path):
        if filename.endswith('.xml'):
            project_name = os.path.splitext(filename)[0]
            projects[project_name] = filename
    return projects


if __name__ == '__main__':
    llm = LLM(model="marinarosell/Mistral-7B-Instruct-v0.3-GPTQ-8bit-gs128", quantization="gptq_marlin", dtype="half",
              max_model_len=8192)
    input_base_path = sys.argv[1]
    projects = get_projects_from_base_path(input_base_path)

    for project_name in tqdm(projects.keys(), desc="Processing All Projects"):
        print(f"\n--- Processing Project: {project_name} ---")

        project_json_dir = os.path.join("cached_methods", project_name)
        if not os.path.exists(project_json_dir):
            print(f"Warning: Directory not found for project: {project_json_dir}")
            continue

        for json_file in os.listdir(project_json_dir):
            if not json_file.endswith(".json"):
                continue

            sample_path = os.path.join(project_json_dir, json_file)
            print(f"Processing file: {sample_path}")

            # sample_path = "cached_methods/dubbo/Cache_Res50_C1.json"

            # load the json to dictionary
            df = load_dataframe(sample_path)

            # convert this to json string
            json_string = JSON_File_IO.convert_Dataframe_to_JSON_string(df)

            # iterate over the json string
            json_bugs = json.loads(json_string)

            # iterate over the json array
            for bug in tqdm(json_bugs, desc="Processing JSON Bugs"):
                # for bug in json_bugs:
                bug_title = html.unescape(bug['bug_title'])
                bug_description = html.unescape(bug['bug_description'])
                project = bug['project']
                buggy_commit = bug['buggy_commit']
                # sub_project = bug['sub_project']
                # version = bug['version']
                es_results = bug['es_results']

                score_llm_results = llm_scoring(es_results, bug_title, bug_description, llm=llm)

                bug['es_results'] = score_llm_results

            output_dir = os.path.join("Output", "Intelligent_Feedback", project_name)
            os.makedirs(output_dir, exist_ok=True)

            output_filename = f"Scored_{json_file}"
            JSON_File_IO.save_Dict_to_JSON(json_bugs, output_dir, output_filename)