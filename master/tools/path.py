import os


def is_folder_empty(folder_path: str) -> bool:
    """
    Checks if the specified folder is empty.
    Args:
        folder_path (str): Path to the folder.
    Returns:
        bool: True if the folder is empty, False otherwise.
    """
    if not os.path.isdir(folder_path):
        raise ValueError(f"The path {folder_path} is not a valid folder.")
    # List all entries in the folder
    return len(os.listdir(folder_path)) == 0
