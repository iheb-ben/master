from pathlib import Path


def load_modules():
    default_addons_path = str(Path('.').joinpath('master/addons').absolute().resolve())
