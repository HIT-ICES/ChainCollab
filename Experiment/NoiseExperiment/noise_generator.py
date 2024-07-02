import random
import argparse

parser = argparse.ArgumentParser()
# subparsers = parser.add_subparsers()

my_description = (
    "Takes a text log and generates n noise logs from it,"
    "by removing events, adding events, and switching events"
    "at random."
)


def init_parser(parser):
    parser.add_argument(
        "-n", type=int, help="Amount of noise logs to generate.", default=1
    )
    parser.add_argument("-f", help="input file name", required=True)
    parser.add_argument(
        "-a",
        help="add-list file name, containing all possible lines to add",
        required=True,
    )
    parser.add_argument("-o", help="output directory name", required=True)
    parser.add_argument("-i", help="input directory name", required=True)
    parser.set_defaults()


# def subcommand(args):


def rnd_noise_gen_func(args):

    #    import time
    #    import sys
    # import math

    # read file
    filename = args.f
    fo = open(args.i + filename, "r")
    lines = fo.readlines()
    fo.close()

    fo2 = open(args.a, "r")
    addListLines = fo2.readlines()
    fo2.close()

    filenamename = filename
    filenameext = ""
    if filename.endswith(".log") or filename.endswith(".txt"):
        filenamename = filename[:-4]
        filenameext = filename[-4:]

    n = abs(args.n)
    for i in range(n):
        newFilename = filenamename + "-noise-" + str(i).zfill(2) + filenameext
        print("New file: " + newFilename)
        newFile = open(args.o + newFilename, "w")
        # clone the original lines
        linesClone = list(lines)
        noLines = len(linesClone)
        # iterate through the three options: add, del, switch
        if i % 3 == 0:
            lineToDel = int(random.random() * noLines)
            print("Deleting line " + str(lineToDel))
            linesClone.pop(lineToDel)
        elif i % 3 == 1:
            idxLineToAdd = int(random.random() * len(addListLines))
            addedLine = addListLines[idxLineToAdd]
            idxToAddLine = int(random.random() * noLines)
            print(
                "Adding line at " + str(idxToAddLine) + " ; line to add: " + addedLine
            )
            linesClone.insert(idxToAddLine, addedLine)
        else:
            lineToSwitch = int(random.random() * (noLines - 1))
            print(
                "Switching lines " + str(lineToSwitch) + " and " + str(lineToSwitch + 1)
            )
            line = linesClone.pop(lineToSwitch)
            linesClone.insert(lineToSwitch + 1, line)
        for line in linesClone:
            newFile.write(line)
        newFile.close()


if __name__ == "__main__":
    #    my_parser = parser.add_parser("random_noise_gnerator", description=my_description)
    init_parser(parser)
    args = parser.parse_args()
    #    args.subcommand(args)
    rnd_noise_gen_func(args)
