import functools
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, List, Optional, ParamSpec, TypeVar, Union

from pyperclip import copy  # type: ignore

from utils.configs import CACHE, ON_ANDROID


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


def set_cache(filename: str, data: Union[dict[str, Any], list[Any]]) -> None:
    """
    Store JSON data into a cache file.

    Args:
        filename (str): Path to the JSON cache file.
        data (dict | list): Data to store.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_cache(filename: str) -> Optional[Union[dict[str, Any], list[Any]]]:
    """
    Retrieve JSON data from a cache file.

    Args:
        filename (str): Path to the JSON cache file.

    Returns:
        dict | list | None: Retrieved data, or None if the file doesn't exist.
    """
    if not os.path.exists(filename):
        return None

    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


P = ParamSpec("P")
R = TypeVar("R", bound=Any)


def cached(
    filename_getter: Callable[P, str],
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator that caches a function's JSON-serializable result
    under ./cache/<filename>.json using existing get_cache/set_cache.

    Args:
        filename_getter (Callable[..., str]): Function returning the
            base filename (without path or extension).

    Returns:
        Callable: Decorated function that caches its result.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            CACHE.mkdir(parents=True, exist_ok=True)
            filename = str(CACHE / f"{filename_getter(*args, **kwargs)}.json")

            data = get_cache(filename)
            if data is not None:
                return data  # type: ignore[return-value]

            data = func(*args, **kwargs)
            set_cache(filename, data)
            return data

        return wrapper

    return decorator
