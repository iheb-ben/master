from pathlib import Path
from tempfile import gettempdir


def temporairy_directory():
    directory_path = Path(gettempdir()).joinpath('.master')
    if not directory_path.exists():
        directory_path.mkdir()
    return directory_path
