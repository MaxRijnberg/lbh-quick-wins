import pathlib, re
from typing import Union, List


def get_most_recent_version(
    dir_path: Union[pathlib.Path, str], file_name: str, file_type: str
) -> int:
    """
    Get the most recent version number for files following a pattern.

    Args:
        dir_path (Union[pathlib.Path, str]): Directory containing versioned files.
        file_name (str): The filename you want to search for (e.g. 'eda').
        file_type (str, optional): The filetype you want to search for (usually the Markdown). Defaults to ".md".

    Returns:
        int: The most recent version number present in the directory.
    """
    if isinstance(dir_path, str):
        dir_path = pathlib.Path(dir_path)
    files = list(dir_path.glob(f"{file_name}_v*{file_type}"))
    if not files:
        return 0

    versions: List[int] = []
    for file in files:
        match = re.search(rf"{file_name}_v(\d+)", file.name)
        if match:
            versions.append(int(match.group(1)))
    return max(versions)
