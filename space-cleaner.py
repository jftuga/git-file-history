#!/usr/bin/env python3

# Source code space cleaner utility
# Removes extraneous spaces from source files while preserving proper indentation.
# Moves the original file to /tmp and saves a cleaned version in place.

import argparse
import shutil
from pathlib import Path


def clean_spaces_from_lines(lines: list[str]) -> list[str]:
    """
    Remove trailing whitespace from all lines and convert space-only lines to empty lines.

    Args:
        lines: List of strings representing file lines

    Returns:
        List of cleaned lines with trailing whitespace removed
    """
    cleaned_lines = []

    for line in lines:
        # Remove trailing whitespace (including spaces and tabs)
        cleaned_line = line.rstrip()
        cleaned_lines.append(cleaned_line)

    return cleaned_lines


def backup_file_to_tmp(file_path: Path) -> Path:
    """
    Move the original file to /tmp directory as a backup.

    Args:
        file_path: Path object pointing to the file to backup

    Returns:
        Path object pointing to the backup file location

    Raises:
        FileNotFoundError: If the source file doesn't exist
        PermissionError: If unable to move file to /tmp
    """
    backup_path = Path("/tmp") / file_path.name

    # If backup already exists, add a number suffix
    counter = 1
    original_backup_path = backup_path
    while backup_path.exists():
        stem = original_backup_path.stem
        suffix = original_backup_path.suffix
        backup_path = Path("/tmp") / f"{stem}_{counter}{suffix}"
        counter += 1

    shutil.move(str(file_path), str(backup_path))
    return backup_path


def process_source_file(file_path: str, remove_backup: bool = False) -> None:
    """
    Process a source file by removing extraneous spaces and backing up the original.

    Args:
        file_path: String path to the source file to process
        remove_backup: If True, remove backup file after successful operation

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        PermissionError: If unable to read/write files
        UnicodeDecodeError: If file contains invalid text encoding
    """
    source_path = Path(file_path)

    if not source_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not source_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    # Read the original file
    try:
        with open(source_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        with open(source_path, 'r', encoding='latin-1') as file:
            lines = file.readlines()

    # Clean the lines
    cleaned_lines = clean_spaces_from_lines(lines)

    # Backup original file to /tmp
    backup_path = backup_file_to_tmp(source_path)
    print(f"Original file backed up to: {backup_path}")

    # Write cleaned content to the original location
    with open(source_path, 'w', encoding='utf-8') as file:
        for line in cleaned_lines:
            file.write(line + '\n')

    print(f"Cleaned file saved: {source_path}")

    # Remove backup file if requested and operation was successful
    if remove_backup:
        backup_path.unlink()
        print(f"Backup file removed: {backup_path}")
    else:
        print(f"Backup file retained: {backup_path}")


def main() -> None:
    """
    Main function to handle command line arguments and process the specified file.
    """
    parser = argparse.ArgumentParser(
        description="Remove extraneous spaces from source code files. "
                   "Backs up original to /tmp and saves cleaned version in place."
    )

    parser.add_argument(
        'file',
        help='Path to the source file to clean'
    )

    parser.add_argument(
        '-r', '--remove',
        action='store_true',
        help='Remove backup file from /tmp after successful operation'
    )

    args = parser.parse_args()

    try:
        process_source_file(args.file, args.remove)
        print("File processing completed successfully.")
    except (FileNotFoundError, PermissionError, ValueError, UnicodeDecodeError) as e:
        print(f"Error: {e}")
        exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
