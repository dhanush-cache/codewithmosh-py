import re
import subprocess
from pathlib import Path
from typing import List

from pyperclip import copy  # type: ignore

from utils.configs import ON_ANDROID


def copy_to_clipboard(text: str, label: str = "Text", quiet: bool = False) -> None:
    """
    Copies the given text to the clipboard.

    Parameters:
    text (str): The text to be copied to the clipboard.
    label (str, optional): A label to describe the text being copied. Defaults to "Text".
    quiet (bool, optional): If set to True, suppresses the print statement. Defaults to False.

    Returns:
    None
    """
    if ON_ANDROID:
        __termux_copy(text, label)
    else:
        copy(text)
    if not quiet:
        print(f"{label}: {text} copied...✔")


def __termux_copy(text: str, label: str):
    try:
        subprocess.run(
            ["termux-clipboard-set"],
            input=text.encode(),
            check=True,
            timeout=5,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        print(f"{label}: {text}")


def clean_path(path: Path) -> Path:
    """
    Cleans a Path object by removing or replacing troubling characters
    in *all parts* of the path (directories + filename).
    Returns a new Path object.
    """

    mapping = {
        "?": "",
        "*": "",
        ":": " -",
        '"': "'",
        "<": "",
        ">": "",
        "|": "-",
        "\\": "",
        "\t": " ",
        "\n": " ",
        "\r": " ",
    }

    path_str = str(path)
    for bad, replacement in mapping.items():
        path_str = path_str.replace(bad, replacement)

    return Path(re.sub(r"\s+", " ", path_str))


def course_exists(target_list: List[Path]) -> bool:
    for target in target_list:
        if not target.exists():
            return False
    return True
