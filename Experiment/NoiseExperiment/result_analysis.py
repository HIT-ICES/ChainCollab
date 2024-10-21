import os
import json


def detect_single_operation_change(initial_path, current_path):
    len_initial = len(initial_path)
    len_current = len(current_path)

    # Check if the only difference is an addition
    if len_current > len_initial:
        for i in range(len_initial):
            if initial_path[i] != current_path[i]:
                return [f"add {current_path[i]} before {initial_path[i]}"]
        return [f"add {current_path[-1]} before {max(initial_path) + 1}"]

    # Check if the only difference is a deletion
    elif len_current < len_initial:
        for i in range(len_current):
            if initial_path[i] != current_path[i]:
                return [f"delete {initial_path[i]}"]
        return [f"delete {initial_path[-1]}"]

    # Check for swaps (only one operation allowed)
    else:
        swap_candidates = []
        for i in range(len_initial):
            if initial_path[i] != current_path[i]:
                swap_candidates.append((initial_path[i], current_path[i]))

        if (
            len(swap_candidates) == 2
            and swap_candidates[0][0] == swap_candidates[1][1]
            and swap_candidates[0][1] == swap_candidates[1][0]
        ):
            return [f"swap {swap_candidates[0][0]} and {swap_candidates[0][1]}"]

    return []


# read result from file
def read_result(file_path):
    with open(file_path, "r") as file:
        lines = file.readlines()
        result = []
        for line in lines:
            result.append(list(map(int, line.split())))
    return result


def load_json_files_into_arrays(root_dir):

    # Dictionary to hold the arrays of json objects, keyed by the 'result' directory path
    results = {}

    # Walk through the directory structure
    for root, dirs, files in os.walk(root_dir):
        # Check if we're currently in a 'result' directory
        if "result" in root:
            # Create a list to store all JSON objects for this 'result' folder
            json_files = []
            # Process each file in the directory
            for file in files:
                # Check if the file is a JSON file
                if file.endswith(".json"):
                    file_path = os.path.join(root, file)
                    # Load the JSON file
                    try:
                        with open(file_path, "r") as f:
                            # Load the file's content as a JSON object
                            json_object = json.load(f)
                            basic_path_result, other_path_result = parse_json_result(
                                json_object[0]
                            )
                            # Add the JSON object to the list
                            json_files.append(
                                {
                                    "file_name": file,
                                    "basic_path_result": basic_path_result,
                                    "other_paths_result": other_path_result,
                                }
                            )
                    except Exception as e:
                        print(f"Error loading {file_path}: {e}")
            # Add the list to the dictionary, keyed by the result folder path
            results[root] = json_files
            # writr the result to a json file
            with open(root + "/result.json", "w") as f:
                json.dump(json_files, f)
    return results


def parse_json_result(data):
    # Extract the first index_path as basic_path and the rest to an array
    basic_path = {
        "index_path": data["results"][0]["index_path"],
        "tag": data["results"][0]["tag"],
    }
    other_index_paths = [
        {
            "index_number": index + 1,
            "index_path": result["index_path"],
            "operation": detect_single_operation_change(
                basic_path["index_path"], result["index_path"]
            ),
            "tag": result["tag"],
        }
        for index, result in enumerate(data["results"][1:])
    ]
    other_index_paths.sort(key=lambda x: x["operation"])

    return basic_path, other_index_paths


if __name__ == "__main__":
    # Replace 'your_path_to_done_directory' with the actual path to your 'done' directory
    path_to_done = "/home/qkl02-ljl/code/IBC/Experiment/NoiseExperiment/done"
    result_arrays = load_json_files_into_arrays(path_to_done)
    print(result_arrays)

    # # Initial and current paths
    # initial_path = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    # current_path = [0, 1, 2, 3, 4, 10, 6, 7, 8, 9, 5]

    # # Detect changes between initial_path and current_path
    # detected_changes = detect_single_operation_change_v2(initial_path, current_path)

    # # Print detected changes
    # print(detected_changes)
