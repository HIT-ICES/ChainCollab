import json
import sys
import os

if __name__ == "__main__":
    if len(sys.argv) <2:
        print("Pls Provide result path")
    directory_path = sys.argv[1]
    
    if not os.path.isdir(directory_path):
        print(f"提供的路径无效：{directory_path}")
        sys.exit(1)

    basic_path_dir = os.path.join(directory_path,"basic_path")
    output_path_dir = os.path.join(directory_path,"result")
    
    basic_files = {file for file in os.listdir(basic_path_dir)
                   if os.path.isfile(os.path.join(basic_path_dir, file)) and file.endswith(".json") and not file.endswith("_patch.json") and not file.endswith("_result.json")}
    output_files = {file for file in os.listdir(output_path_dir)
                  if os.path.isfile(os.path.join(output_path_dir,file)) and file.endswith(".json") and not file.endswith("_patch.json")}

    common_part = basic_files & output_files

    file_pairs = [(os.path.join(basic_path_dir, file), os.path.join(output_path_dir, file)) for file in common_part]


    for origin_file, file in file_pairs:
        with open(file, "r") as f:
            content = json.load(f)
        index_paths_to_reExperiment = [(result_item["index_path"], index) for index, result_item in enumerate(content[0]["results"]) if result_item["tag"]==1]
        with open(origin_file, "r") as f:
            content = json.load(f)
        content[0]["appended_index_paths"] = [item[0] for item in index_paths_to_reExperiment]
        with open(origin_file.replace(".json","_patch.json"), "w") as f:
            json.dump(content, f)
        with open(origin_file.replace(".json","_index_mapping_patch.json"), "w") as f:
            json.dump(index_paths_to_reExperiment, f)

