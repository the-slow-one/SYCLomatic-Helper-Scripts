#!/usr/bin/python3
import csv
import logging
import os
import shutil
import subprocess

from collections import defaultdict

REPO_LIST_FILE = "repo.txt"
# NOTE: For grep to work provide the absolute path
REPO_ROOT = os.path.join(os.getcwd(), "apps")
RESULTS_PATH = os.path.join(os.getcwd(), "results")
#SRC_EXTN = [".h", ".hpp", ".c", ".cpp", ".cu", ".cuh"]
SRC_EXTN = [".cmake", "CMakeLists.txt"]


class SearchResult:
    def __init__(self):
        self._filepath = None
        self.lineno = None
        self.api = None
        self.projectname = None

    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, filepath):
        self._filepath = filepath
        self.projectname = filepath.split(os.sep)[0]


def chunks(filepaths):
    """
    Return multiple list of size 10,000 each
    """
    chunk_size = 10000
    for i in range(0, len(filepaths), chunk_size):
        yield filepaths[i:i+chunk_size]

def log_msg(msg):
    logging.debug(msg)


def run_cmd(cmd, wd):
    """
    Run command in given directory.
    """
    try:
        process = subprocess.run(
            cmd, cwd=wd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    except subprocess.SubprocessError as evar:
        log_msg(f"Error executing command {' '.join(cmd)}")
        log_msg(f"Error: {evar}")
        return None

    return process


def check_cmd_status(cmd, wd=None):
    """
    Run command in given directory and returns True is command succeeds.
    """
    process = run_cmd(cmd, wd=wd)

    if not process:
        log_msg(f"Failed to create process for command {' '.join(cmd)}")
        log_msg(f"Error: {evar}")

    status = process.returncode == 0

    if not status:
        log_msg(f"Non-zero return code for command: '{' '.join(cmd)}'")
        log_msg(f"{process.stdout=}")
        log_msg(f"{process.stderr=}")
        return False

    return status


def gh_clone(url, repo_root):
    """
    Clone the URL at given repo_root with depth as one.
    """
    if not url.endswith(".git"):
        log_msg(f"Unsupported URI: '{url}'")
        return False

    try:
        repo_name = os.path.basename(url).rsplit(".", 1)[0]
        src_path = os.path.join(repo_root, repo_name)

        if os.path.exists(src_path):
            log_msg(f"{src_path} exist. NOT cloning {url}")
            return True

    except Exception as evar:
        log_msg(f"Failed check for source existence: {evar}")

    print(f"Cloning {url}... ", end="", flush=True)

    cmd = ["git", "clone", "--depth", "1", url]
    if not check_cmd_status(cmd, wd=repo_root):
        log_msg(f"Failed to clone {url}")
        print("failed")
        return False

    print("done")
    return True


def clone_repos(repo_list_path, repo_root):
    """
    Read given file and expect the git based URL in it.
    """
    if not repo_list_path or not os.path.isfile(repo_list_path):
        log_msg(f"Missing file: {repo_list_path}")
        return True

    if not os.path.isdir(repo_root):
        os.mkdir(repo_root)

    atleast_one_cloned = False
    with open(repo_list_path) as fhandle:
        for url in fhandle.readlines():
            if url.startswith('#'):
                continue
            atleast_one_cloned |= gh_clone(url.strip(), repo_root)

    return atleast_one_cloned


def get_filepaths_to_search(repo_root):
    global SRC_EXTN
    filepaths = []
    for root, _, filenames in os.walk(repo_root):
        for filename in filenames:
            _, extn = os.path.splitext(filename)
            if extn in SRC_EXTN:
                filepaths.append(os.path.join(root, filename))

    return filepaths


def get_api_list():
    try:
        with open("api.txt") as fhandle:
            return [api.strip() for api in fhandle.readlines()]

    except OSError as evar:
        log_msg(f"Failed to read API list file: {evar}")

    return []


def extract_search_results(byte_stream):
    """ """
    search_results = []
    try:
        for grep_result_line in byte_stream.decode("utf-8").split():
            filepath, lineno, srcline = grep_result_line.split(":")
            result = SearchResult()
            result.filepath = filepath[len(REPO_ROOT) + 1 :]
            result.lineno = lineno
            search_results.append(result)

    except UnicodeError as evar:
        log_msg(f"Not processing grep result due to decode error: {evar}")

    except ValueError as evar:
        log_msg(f"Missing grep output format (filename:lineno:result): {evar}")

    return search_results


def search_api(api, filepaths):
    if not filepaths:
        return

    results = []

    cmd = ["grep", "-nHow", f"{api}" ]
    cmd.extend(filepaths)
    try:
        process = run_cmd(cmd, wd=REPO_ROOT)

        if process and process.returncode == 0:
            results = extract_search_results(process.stdout)
            for result in results:
                result.api = api

    except OSError as evar:
        log_msg(f"grep failed while searching {api}: {evar}")

    return results

def print_results(results):
    """
    Dump search results in concise format.
    """
    api_project_count = defaultdict(lambda: defaultdict(list))
    for result in results:
        api_project_count[result.api][result.projectname].append((result.filepath, result.lineno))

    for api, project_details in api_project_count.items():
        print(api)
        for projectname, locations in project_details.items():
            print(f"  {projectname}: {len(locations)}")

    gen_top_csv(api_project_count)

def gen_top_csv(results):
    """
    """
    global RESULTS_PATH

    api_rows = []
    project_names = []

    if os.path.isdir(RESULTS_PATH):
        shutil.rmtree(RESULTS_PATH, ignore_errors=True)

    os.mkdir(RESULTS_PATH)

    for api, project_details in results.items():
        api_row = [api]

        if not project_names:
            project_names = list(project_details.keys())

        for project_name in project_names:
            api_row.append(len(project_details[project_name]))

        api_rows.append(api_row)

    header = ["API"] + project_names
    top_result_path = os.path.join(RESULTS_PATH, "top.csv") 
    with open(top_result_path, "w", newline="") as fhandle:
        writer = csv.writer(fhandle, delimiter=',', dialect="excel")
        writer.writerow(header)
        writer.writerows(api_rows)

    gen_project_csv(results, project_names)

def gen_project_csv(results, project_names):
    header = ["API", "Source File Path", "Line number"]

    for project_name in project_names:
        project_result_path = os.path.join(RESULTS_PATH, f"{project_name}.csv") 
        with open(project_result_path, "w", newline="") as fhandle:
            writer = csv.writer(fhandle, delimiter=',', dialect="excel")
            writer.writerow(header)

    for api, project_details in results.items():
        for project_name, locations in project_details.items():
            api_rows = [[api, location[0], location[1]] for location in locations]
            project_result_path = os.path.join(RESULTS_PATH, f"{project_name}.csv") 
            with open(project_result_path, "a", newline="") as fhandle:
                writer = csv.writer(fhandle, delimiter=',', dialect="excel")
                writer.writerows(api_rows)


def begin_search():
    global REPO_ROOT, REPO_LIST_FILE
    if not clone_repos(REPO_LIST_FILE, REPO_ROOT):
        print("Couldn't clone any repo")
        return False

    print(f"Looking for projects in '{REPO_ROOT}'")
    src_files = get_filepaths_to_search(REPO_ROOT)

    apis = get_api_list()
    print(f"Seaching for {len(apis)} APIs in {len(src_files)} source files")

    search_results = []
    for src_file_chunk in chunks(src_files):
        for api in apis:
            result = search_api(api, src_file_chunk)
            if result:
                search_results.extend(result)

    print_results(search_results)
    return True

if "__main__" == __name__:
    log_filename = "search.log"
    logging.basicConfig(
        filename=log_filename,
        filemode="w",
        encoding="utf-8",
        level=logging.DEBUG,
        format="%(levelname)s:%(message)s",
    )
    if not begin_search():
        print(f"See {log_filename}")
        print("Abort!")

# EOF
