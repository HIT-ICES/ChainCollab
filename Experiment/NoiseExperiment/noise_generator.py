import random
import argparse
import os

parser = argparse.ArgumentParser()
# subparsers = parser.add_subparsers()

my_description = (
    "Takes a text log and generates n noise logs from it,"
    "by removing events, adding events, and switching events"
    "at random."
)


def generate_random_seed():
    random_bytes = os.urandom(4)
    return int.from_bytes(random_bytes, byteorder="big")


def reset_random_seed():
    random.seed(generate_random_seed())


def random_int(min, max):
    reset_random_seed()
    return random.randint(min, max)


class RandomMode:
    ADD = "add"
    REMOVE = "remove"
    SWITCH = "switch"
    ALL = "all"

    def __init__(self, mode: str):
        self.mode = mode

    def if_add(self) -> bool:
        return self.ADD in self.mode

    def if_remove(self) -> bool:
        return self.REMOVE in self.mode

    def if_switch(self) -> bool:
        return self.SWITCH in self.mode


def generate_random_path(
    origin_path,
    random_mode: RandomMode,
    random_num: int,
    used_path_add: list[tuple[int]],
    used_path_remove: list[int],
    used_path_switch: list[tuple[int]],
) -> list[tuple]:
    # read origin path
    # generate output accorrding to random_mode and random_num
    origin_path = list(range(len(origin_path)))
    change_method = []
    if random_mode.if_add() and len(used_path_add) > 0:
        change_method.append(RandomMode.ADD)
    if random_mode.if_remove() and len(used_path_remove) > 0:
        change_method.append(RandomMode.REMOVE)
    if random_mode.if_switch() and len(used_path_switch) > 0:
        change_method.append(RandomMode.SWITCH)

    def random_method(input_path: list[int], method: str) -> list[int]:
        input_path = list(input_path)
        match method:
            case RandomMode.ADD:
                add_tuple = random.sample(used_path_add, 1)
                idxToAdd = add_tuple[0][0]
                content_to_input = input_path[idxToAdd]
                idxToInsert = add_tuple[0][1]
                input_path.insert(idxToInsert, content_to_input)
                used_path_add.remove(add_tuple[0])
                return tuple(input_path)
            case RandomMode.REMOVE:
                idxToRemove = random.sample(used_path_remove, 1)
                input_path.pop(idxToRemove[0])
                used_path_remove.remove(idxToRemove[0])
                return tuple(input_path)
            case RandomMode.SWITCH:
                switch_tuple = random.sample(used_path_switch, 1)
                content_to_input = input_path[switch_tuple[0][0]]
                input_path[switch_tuple[0][0]] = input_path[switch_tuple[0][1]]
                input_path[switch_tuple[0][1]] = content_to_input
                used_path_switch.remove(switch_tuple[0])
                return tuple(input_path)
            case _:
                return tuple(input_path)

    for i in range(random_num):
        # choose beteen add, remove, switch according to random_mode
        try:
            random_methods = random.choice(change_method)
        except Exception as e:
            print(e)
        new_path = random_method(tuple(origin_path), random_methods)

    return new_path
