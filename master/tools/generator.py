import string
import random


def generate_unique_string(length=20, ignore_letters=None):
    ignore_letters = ignore_letters or ''
    characters = string.punctuation + string.ascii_letters + string.digits
    if ignore_letters:
        characters = ''.join(char for char in characters if char not in ignore_letters)
    return ''.join(random.choices(characters, k=length))
