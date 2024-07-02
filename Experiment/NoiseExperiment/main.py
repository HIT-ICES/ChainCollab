import os
import sys




def help_message():
    print("This is the help message")
    print("Usage: python main.py [command] [arguments]")
    print("Commands:")
    print("  -h or --help: print this help message")
    print("  -g or --generate [-input ] [-output ] [-n ] [-t add|remove|switch] : generate noise logs")
    print("    -input: input file name")
    print("    -output: output directory name")
    print("    -n: number of noise logs to generate")
    print("    -t: type of noise to generate, including add, remove, and switch, default is all, -t ars")
    print("  -e or --experiment: run the experiment")


def default_response():
    print("Invalid command. Use -h or --help for help.")



if __name__ == "__main__":
    # parse command & arguments, then call the function respective to the command
    # -h or --help will print the help message
    # -g or --generate will call the noise generator
    # -e or --experiment will call the experiment
    if len(sys.argv) == 1:
        default_response()