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


    for file, target_file in file_pairs:
        patch_result = file.replace(".json","_patch_result.json")
        if not os.path.exists(patch_result):
            continue
        mapping = file.replace(".json","_index_mapping_patch.json")
        target_file = target_file
        with open (patch_result, "r") as f:
            res = json.load(f)
        with open(target_file, "r") as f:
            target = json.load(f)
        with open(mapping, "r") as f:
            mapping = json.load(f)
        for i, item in enumerate(res[0]["results"][1:]):
            # skip orgin path 
            target_index = mapping[i][1]
            target[0]["results"][target_index] = item
        with open(target_file.replace(".json","_new.json"), "w") as f:
            json.dump(target,f)