# plainTextToJsonString
# open a .go file and out put a json string, replace " with \", keep \t and \n

import json
import os

args = os.sys.argv  # get the arguments
file_name = args[1]  # get the file name
json_key = args[2]  # get the json key

with open(file_name + ".go", "r") as f:
    lines = f.readlines()
    json_string = ""
    for line in lines:
        # line = line.replace("{", "{{")
        # line = line.replace("}", "}}")
        # line = line.replace('$', '{')
        # line = line.replace('^', '}')
        json_string += line

    with open("snippet.json", "r") as f:
        # judge is json otherwise get an empty json
        try:
            content = json.load(f)
        except:
            content = {}

    content.update({json_key: json_string})

    with open("snippet.json", "w") as f:
        json.dump(content, f)

    with open("snippet.json", "r") as f:
        content = f.read()
    with open("test2.go", "w") as f:
        f.write(content)
