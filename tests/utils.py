import random

from src.side_type import SideType, SIDE_TYPE_TO_CHAR

def isolate_at_index(sequence, index):
    if index >= 0 and index < len(sequence):
        isolated_sequence = sequence[:index] +\
                            "(" +\
                            sequence[index] +\
                            ")" +\
                            sequence[index+1:]
        return isolated_sequence
    return sequence

def get_sequence(side_types, isolate_at_idx=-1):
    return isolate_at_index("".join([SIDE_TYPE_TO_CHAR[type] for type in side_types]), isolate_at_idx)

def get_example_side_sequence(num):
    all_types = SideType.all_types()
    random_types = random.sample(all_types[:-1], num % len(all_types))
    return get_sequence(random_types)