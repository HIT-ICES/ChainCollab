import os
import sys
import json
import argparse

from invoker import invoke_task
from noise_generator import generate_random_path, RandomMode
from loader import step_loader, Task

def get_parser():
    parser = argparse.ArgumentParser(description="This is the help message")

    subparsers = parser.add_subparsers(dest="command")

    # Help command
    parser_help = subparsers.add_parser(
        "help", aliases=["-h", "--help"], help="Print this help message"
    )

    # Run command
    parser_run = subparsers.add_parser(
        "run", aliases=["-r", "--run"], help="Run an experiment"
    )
    parser_run.add_argument("-input", help="Input file name", required=True)
    parser_run.add_argument(
        "-output", help="Output directory name", default="output.json"
    )
    parser_run.add_argument(
        "-n", type=int, help="Number of noise to generate", default=1
    )
    parser_run.add_argument(
        "-N", type=int, help="Number of path to generate", default=10
    )
    parser_run.add_argument(
        "-m",
        help="Mode of noise generation, like ars ar as etc. add|remove|switch including add, remove, and switch, default is all, -t ars",
        default="ars",
    )
    return parser


def default_response():
    print("Invalid command. Use -h or --help for help.")


def run_experiment(
    file, random_mode, random_num=3, experiment_num=10, output="result.json"
):
    task: Task = step_loader(file)

    # generate
    execute_paths = []
    while len(execute_paths) < experiment_num:
        random_path = generate_random_path(task.invoke_path, random_mode, random_num)
        if random_path not in execute_paths:
            execute_paths.append(random_path)

    # execute and output
    results = [{"path":task.invoke_path, "results":[], "original":True}]

    with open(output, "w") as f:
        for path in execute_paths:
            single_result = {"path": path, "results": ""}
            res = invoke_task(path, task.steps)
            single_result["results"] = str(res)
            results.append(single_result)
        json.dump(results, f, indent=4)


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    match args.command:
        case "help":
            parser.print_help()
        case "run":
            random_mode = ""
            for c in args.m:
                if "a" in c:
                    random_mode += RandomMode.ADD
                elif "r" in c:
                    random_mode += RandomMode.REMOVE
                elif "s" in c:
                    random_mode += RandomMode.SWITCH
            run_experiment(
                file=args.input,
                random_mode=RandomMode(random_mode),
                random_num=args.n,
                experiment_num=args.N,
                output=args.output,
            )

        case _:
            default_response()
