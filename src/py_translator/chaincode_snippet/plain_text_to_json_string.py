# plainTextToJsonString
# open a .go file and out put a json string, replace " with \", keep \t and \n

import json
import os

args = os.sys.argv  # get the arguments
file_name = "chaincode_snippet/test.go"


while True:
    command = input(
        """
        Command "Add" "Delete" "Output"\n
          Add json_key -X(if it is a frame or a whole code)\n
          Delete json_key\n
          Output json_key
        """
    )
    action = command.split(" ")[0]
    json_key = command.split(" ")[1]
    other_params = command.split(" ")[2] if len(command.split(" ")) > 2 else None

    match action:
        case "Add":
            with open(file_name, "r") as f:
                lines = f.readlines()
                json_string = ""
                for line in lines:
                    if other_params == "-X":
                        line = line.replace("{", "{{")
                        line = line.replace("}", "}}")
                        line = line.replace("$", "{")
                        line = line.replace("^", "}")
                    json_string += line

                with open("chaincode_snippet/snippet.json", "r") as f:
                    # judge is json otherwise get an empty json
                    try:
                        content = json.load(f)
                    except:
                        content = {}

                content.update({json_key: json_string})

                with open("chaincode_snippet/snippet.json", "w") as f:
                    json.dump(content, f)
        case "Delete":
            with open("chaincode_snippet/snippet.json", "r") as f:
                content = json.load(f)
            content.pop(json_key)
            with open("chaincode_snippet/snippet.json", "w") as f:
                json.dump(content, f)
            break
        case "Output":
            with open("chaincode_snippet/snippet.json", "r") as f:
                content = json.load(f)
            with open(file_name, "w") as f:
                f.write(content[json_key])
            break