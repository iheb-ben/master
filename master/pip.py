import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Union


def install_requirements(requirement_file_path: Union[str, os.PathLike], required: bool = False):
    _logger = logging.getLogger(__name__)
    file_path = Path(requirement_file_path).absolute().resolve()
    if file_path.exists() and file_path.is_file():
        try:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', str(file_path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            _logger.info(f'Requirements from {file_path} installed successfully.')
        except subprocess.CalledProcessError as e:
            if required:
                raise
            _logger.error(f'Error occurred while installing requirements: {e.stderr}', exc_info=True)
    else:
        _logger.warning(f'Requirement file not found: {file_path}')
