import os
import shutil
import tempfile
from os import PathLike, mkdir
from pathlib import Path
from typing import Union, Optional, Generator


def to_path(path: Union[Path, PathLike, str], raise_error: bool = True) -> Path:
    path_obj = Path(path) if not isinstance(path, Path) else path
    if not path_obj.exists() and raise_error:
        raise ValueError(f"Element not found: {path}")
    return path_obj.absolute().resolve()


def create_path(path: Union[Path, PathLike, str]):
    path_obj = to_path(path, False)
    if path_obj.suffix:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.touch(exist_ok=True)
    else:
        path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def iterate_directory(folder_path: Union[Path, PathLike, str], include_hidden: bool = True) -> Generator[Path, None, None]:
    for root, dirs, files in os.walk(folder_path):
        for dir_name in dirs:
            if include_hidden or (not include_hidden and not dir_name.startswith('.')):
                yield Path(root).joinpath(dir_name)
        for file_name in files:
            if include_hidden or (not include_hidden and not file_name.startswith('.')):
                yield Path(root).joinpath(file_name)


def is_folder_empty(folder_path: Union[Path, PathLike, str]) -> bool:
    return not any(iterate_directory(to_path(folder_path)))


def decompress_zip(path: Union[Path, PathLike, str], extract_dir: Optional[str] = None):
    path_obj = to_path(path)
    if not path_obj.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if not zipfile.is_zipfile(path):
        raise ValueError(f"Not a valid ZIP file: {path}")
    if not extract_dir:
        extract_dir = str(create_path(path_obj.with_suffix('')))
    with zipfile.ZipFile(path, 'r') as zip_ref:
        dir_path_obj = create_path(extract_dir)
        if not is_folder_empty(dir_path_obj):
            shutil.rmtree(dir_path_obj)
            dir_path_obj.mkdir(parents=True, exist_ok=True)
        zip_ref.extractall(dir_path_obj)
        return dir_path_obj


temporairy_folder = create_path(Path(tempfile.gettempdir()) / 'master')
temporairy_addons_folder = create_path(temporairy_folder / 'addons')
temporairy_session_folder = create_path(temporairy_folder / 'session')
