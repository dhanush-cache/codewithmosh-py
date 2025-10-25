#!/usr/bin/env python3
import argcomplete
import argparse
import json
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Dict, List

from course import CourseSerializer
from utils.archive import extract_non_videos, extract_videos, merge_zips
from utils.configs import DOWNLOADS, HOME
from utils.download import download_archive, download_magnet, gdrive_direct_download_url
from utils.general import copy_to_clipboard


def list_configs(courses: Dict[str, Any]) -> None:
    """
    Prints a list of available configurations from the given courses dictionary.

    Args:
        courses (Dict[str, Any]): A dictionary where keys are course names and values are course configurations.

    Returns:
        None
    """
    print("Available configurations:")
    for i, course in enumerate(sorted(courses.keys()), 1):
        print(f"{i:02}. {course}")


def load_hook(config: str):
    hook_module = f"hooks.{config}"
    if find_spec(hook_module):
        hook = import_module(hook_module).main
    else:
        hook = merge_zips
    return hook


def get_source(
    config: str,
    course_data: dict[str, Any],
    input_archive: List[str] = [],
    quiet: bool = False,
):
    hook = load_hook(config)
    if input_archive:
        return hook(*[Path(file) for file in input_archive])
    if (DOWNLOADS / f"{config}.zip").exists():
        return hook(DOWNLOADS / f"{config}.zip")
    if (DOWNLOADS / config).is_dir():
        files = [file for file in (DOWNLOADS / config).iterdir()]
        files.sort()
        return hook(*files)

    magnets = course_data["magnets"]
    files: List[Path] = []
    for magnet in magnets:
        if not magnet.startswith("magnet:"):
            url = gdrive_direct_download_url(magnet)
            files.append(download_archive(url))
            continue
        if quiet:
            files.append(download_magnet(magnet))
            continue
        copy_to_clipboard(magnet, quiet=True)
        files.append(download_archive(input("Download Link: ")))

    return hook(*files)


def main() -> None:
    config_file = Path("data.json")
    data = json.loads(config_file.read_text())
    courses = data["configs"]

    parser = argparse.ArgumentParser(
        prog="Code With Mosh",
        description="Organizes courses from codewithmosh.com",
        epilog="Checkout https://codewithmosh.com",
    )
    parser.add_argument("config", type=str, help="The configuration to use", choices=courses.keys())
    parser.add_argument(
        "-l",
        "--list-configs",
        action="store_true",
        help="List all available configurations",
    )
    parser.add_argument(
        "-i", "--input-archive", nargs="+", help="Path to the input file"
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Disable manual interactions",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.list_configs:
        list_configs(courses)
        parser.exit()

    if not args.config:
        parser.error("The following arguments are required: config")

    course_data = courses[args.config]

    slug, template_id, *others = course_data.values()
    intro, others = data["templates"][template_id]

    source = get_source(args.config, course_data, args.input_archive, args.quiet)

    course = CourseSerializer.get_course(slug)
    target = HOME / "Programming Videos"
    target_list = course.get_videos(target)
    extract_videos(source, target_list, ffmpeg=True, intro=intro, others=others)
    extract_non_videos(source, target / str(course))


if __name__ == "__main__":
    main()
