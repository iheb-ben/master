from typing import Union
from pathlib import Path
from tempfile import gettempdir
import os


def is_folder_empty(path: Union[str, os.PathLike], raise_error: bool = True) -> bool:
    """
    Checks if the specified directory is empty.
    Args:
        path (Union[str, os.PathLike]): The path to the directory to check.
        raise_error (bool): If True, raises a ValueError when the path does not exist or is not a directory.
                            If False, returns False instead of raising an error.
    Returns:
        bool: True if the directory exists and is empty, False otherwise.
    Raises:
        ValueError: If the path does not exist or is not a directory, and raise_error is True.
    """
    if not os.path.exists(path):
        if not raise_error:
            return False
        raise ValueError(f"The path '{path}' does not exist.")
    if not os.path.isdir(path):
        if not raise_error:
            return False
        raise ValueError(f"The path '{path}' is not a directory.")
    return len(os.listdir(path)) == 0


def temporairy_directory() -> Path:
    """
    Creates and returns a temporary directory specific to the application.

    This method ensures a subdirectory named `.master` exists within the system's
    default temporary directory (as determined by `tempfile.gettempdir()`).
    If the directory does not already exist, it is created.

    :return: A `Path` object representing the `.master` directory inside the temporary directory.
    """
    directory_path = Path(gettempdir()).joinpath('.master')
    if not directory_path.exists():
        directory_path.mkdir()
    return directory_path
