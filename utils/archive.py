import shutil
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Callable, List, Optional
from zipfile import BadZipFile, ZipFile

from natsort import natsorted
from tqdm import tqdm

from archive import MoshZip
from ffmpeg import ffprocess
from utils.configs import TEMP
from utils.general import clean_path


def extract_videos(
    archive: Path,
    target_list: List[Path],
    ffmpeg: bool = False,
    intro: int = 0,
    others: int = 0,
) -> None:
    """
    Extracts video files from a given archive and processes them.
    Args:
        archive (Path): The path to the archive file containing the videos.
        target_list (List[Path]): A list of target paths where the extracted videos will be saved.
        ffmpeg (bool, optional): If True, use ffmpeg to process the videos. Defaults to False.
        intro (int, optional): Timestamp thumbnails of intro videos. Defaults to 0.
        others (int, optional): Timestamp for thumbnails of other videos. Defaults to 0.
    Returns:
        None
    """

    with MoshZip(archive) as zip_ref:
        archived_videos = zip_ref.namelist_from_ext(".mp4", ".mkv")
        print("Processing videos...")
        for video_path, target in tqdm(list(zip(archived_videos, target_list))):
            archived_video = zip_ref.open(video_path)
            archived_path = Path(archived_video.name)
            subtitles = zip_ref.extract_subtitles(video_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if ffmpeg:
                with NamedTemporaryFile(suffix=archived_path.suffix) as temp:
                    video = Path(temp.name)
                    video.write_bytes(archived_video.read())
                    timestamp = intro if target.name.startswith("01") else others
                    ffprocess(video, target, timestamp, subtitles)
                    continue
            target.write_bytes(archived_video.read())
            if subtitles:
                target.with_suffix(subtitles.suffix).write_bytes(subtitles.read_bytes())


def extract_non_videos(source: Path, target_dir: Path) -> None:
    """
    Extracts non-video files (e.g., .zip, .pdf) from a given zip archive to a target directory.

    Args:
        source (Path): The path to the source zip file.
        target_dir (Path): The directory where the extracted files will be saved.

    Returns:
        None
    """
    with MoshZip(source) as zip_ref:
        non_videos = (
            video
            for video in natsorted(zip_ref.namelist())
            if video in zip_ref.namelist_from_ext(".zip", ".pdf")
        )
        print("\nProcessing other files...")
        for video in tqdm(list(non_videos)):
            target = clean_path(target_dir / "Files" / video)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zip_ref.read(video))


def merge_zips(
    *archives: Path, post_process: Optional[Callable[[Path], Path]] = None
) -> Path:
    """
    Merges multiple ZIP archives or directories into a single ZIP archive.

    Args:
        *archives (Path): One or more paths to ZIP archives or directories to be merged.
        post_process (callable, optional): A function that takes a Path and returns a Path.
                                           This function is executed after extraction and before archiving. Defaults to None.

    Returns:
        Path: The path to the resulting merged ZIP archive.

    Raises:
        BadZipFile: If any of the input ZIP files are corrupted.

    Notes:
        - If only one ZIP archive is provided, it will be returned as is.
        - The function creates a temporary directory to unpack the contents of the provided archives or directories.
        - The contents are then repacked into a new ZIP archive, which is saved in a temporary file.
    """
    if len(archives) == 1 and archives[0].suffix == ".zip" and not post_process:
        return archives[0]
    with TemporaryDirectory(dir=TEMP) as temp_dir:
        temp_dir = Path(temp_dir)
        print("Unpacking archives...")
        for part_index, archive in enumerate(tqdm(archives)):
            if archive.is_dir():
                shutil.move(str(archive), temp_dir / f"{part_index}")
                continue
            with ZipFile(archive, "r") as zip_ref:
                for member in zip_ref.namelist():
                    try:
                        zip_ref.extract(member, temp_dir / f"{part_index}")
                    except BadZipFile:
                        print(f"Error: {member} skipped.")

        if post_process:
            temp_dir = post_process(temp_dir)

        with NamedTemporaryFile(dir=TEMP, delete=False, suffix=".zip") as output_zip:
            with ZipFile(output_zip, "w") as zipf:
                for file in tqdm(list(temp_dir.rglob("*")), desc="Repacking archive"):
                    zipf.write(file, file.relative_to(temp_dir))
            return Path(output_zip.name)


def add_file_to_zip(zip_path: Path, file_to_add: Path, after: str) -> None:
    """
    Adds a file to an existing ZIP archive, renaming it based on an existing file in the archive.

    Args:
        zip_path (Path): The path to the ZIP archive.
        file_to_add (Path): The path to the file to be added to the ZIP archive.
        after (str): A string to match against existing file names in the ZIP archive. The new file will be renamed based on the first match.

    Returns:
        None
    """
    with zipfile.ZipFile(zip_path, "a") as zipf:
        target_file = Path(next(filter(lambda x: after in x, zipf.namelist())))
        arcname = target_file.with_stem(target_file.stem + "0")
        zipf.write(file_to_add, arcname=arcname)
