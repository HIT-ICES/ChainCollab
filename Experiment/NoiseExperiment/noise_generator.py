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
    return int.from_bytes(random_bytes, byteorder='big')  

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


def generate_random_path(origin_path, random_mode: RandomMode, random_num: int) -> list[tuple]:
    # read origin path
    # generate output accorrding to random_mode and random_num
    change_method = []

    if random_mode.if_add():
        change_method.append(RandomMode.ADD)
    if random_mode.if_remove():
        change_method.append(RandomMode.REMOVE)
    if random_mode.if_switch():
        change_method.append(RandomMode.SWITCH)

    def random_method(input_path:tuple, method:str)->tuple:
        input_path = list(input_path)
        match method:
            case RandomMode.ADD:
                idxToAdd = random_int(0, len(input_path)-1)
                content_to_input = input_path[idxToAdd]
                idxToInsert = random_int(0, len(input_path)-1)
                input_path.insert(idxToInsert, content_to_input)
                return tuple(input_path)
            case RandomMode.REMOVE:
                idxToRemove = random_int(0, len(input_path)-1)
                input_path.pop(idxToRemove)
                return tuple(input_path)
            case RandomMode.SWITCH:
                idxToSwitch = random_int(0, len(input_path)-1)
                content_to_input = input_path[idxToSwitch]
                idxToSwitchWith = random_int(0, len(input_path)-1)
                input_path[idxToSwitch] = input_path[idxToSwitchWith]
                input_path[idxToSwitchWith] = content_to_input
                return tuple(input_path)
            case _:
                return tuple(input_path)

        

    for i in range(random_num):
        # choose beteen add, remove, switch according to random_mode
        random_methods = random.choice(change_method)
        new_path = random_method(tuple(origin_path), random_methods)
    
    return new_path

