#!/usr/bin/env python3

# Git File Version Extractor
# This script traverses a git repository to extract different versions of a specified file
# throughout its commit history. It saves each version with a timestamp-based filename
# and provides options to filter by date or limit the number of versions extracted.

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class GitFileExtractor:
    """Extracts different versions of a file from git history."""

    def __init__(self, repo_path: Path = Path.cwd(), verbose: bool = False):
        """
        Initialize the extractor with a repository path.

        Args:
            repo_path: Path to the git repository (defaults to current directory)
            verbose: Whether to print git commands being executed
        """
        self.repo_path = repo_path
        self.verbose = verbose

    def _run_git_command(self, command: list[str]) -> str:
        """
        Execute a git command and return its output.

        Args:
            command: List of command arguments to pass to git

        Returns:
            Command output as string

        Raises:
            RuntimeError: If the git command fails
        """
        full_command = ["git"] + command

        if self.verbose:
            print()
            print(f"Running: {' '.join(full_command)}")

        try:
            result = subprocess.run(
                full_command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr.strip()}")

    def _is_git_repository(self) -> bool:
        """
        Check if the current directory is a git repository.

        Returns:
            True if it's a git repository, False otherwise
        """
        try:
            self._run_git_command(["rev-parse", "--git-dir"])
            return True
        except RuntimeError:
            return False

    def _get_file_commits(self, filepath: str, after_date: Optional[str] = None) -> list[tuple[str, str]]:
        """
        Get list of commits that modified the specified file.

        Args:
            filepath: Path to the file in the repository
            after_date: Optional date filter in ISO format (YYYY-MM-DD)

        Returns:
            List of tuples containing (commit_hash, commit_date)
        """
        command = ["log", "--pretty=format:%H|%ci"]

        if after_date:
            command.append(f"--after={after_date}")

        command.extend(["--follow", filepath])

        try:
            output = self._run_git_command(command)
        except RuntimeError as e:
            if "does not exist" in str(e).lower() or "bad revision" in str(e).lower():
                raise FileNotFoundError(f"File '{filepath}' not found in git history")
            raise

        if not output:
            return []

        commits = []
        for line in output.split('\n'):
            if '|' in line:
                commit_hash, commit_date = line.split('|', 1)
                commits.append((commit_hash.strip(), commit_date.strip()))

        return commits

    def _format_timestamp(self, commit_date: str) -> str:
        """
        Format commit date to YYYYmmdd.HHMMSS format.

        Args:
            commit_date: Git commit date string

        Returns:
            Formatted timestamp string
        """
        # Parse git date format: "2025-07-22 01:02:03 +0000"
        try:
            # Remove timezone info for parsing, we'll keep original timezone semantics
            date_part = commit_date.rsplit(' ', 1)[0]
            dt = datetime.strptime(date_part, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y%m%d.%H%M%S")
        except ValueError:
            # Fallback: use current timestamp if parsing fails
            return datetime.now().strftime("%Y%m%d.%H%M%S")

    def _get_file_content_at_commit(self, filepath: str, commit_hash: str) -> str:
        """
        Get file content at a specific commit.

        Args:
            filepath: Path to the file in the repository
            commit_hash: Git commit hash

        Returns:
            File content as string
        """
        return self._run_git_command(["show", f"{commit_hash}:{filepath}"])

    def _generate_output_filename(self, filepath: str, timestamp: str) -> Path:
        """
        Generate output filename with timestamp.

        Args:
            filepath: Original file path
            timestamp: Formatted timestamp string

        Returns:
            Path object for the output file
        """
        original_path = Path(filepath)
        stem = original_path.stem
        suffix = original_path.suffix

        new_filename = f"{stem}-{timestamp}{suffix}"
        return original_path.parent / new_filename

    def extract_versions(self, filepath: str, after_date: Optional[str] = None,
                        max_versions: Optional[int] = None) -> int:
        """
        Extract different versions of a file from git history.

        Args:
            filepath: Path to the file in the repository
            after_date: Optional date filter in ISO format (YYYY-MM-DD)
            max_versions: Optional maximum number of versions to extract

        Returns:
            Number of versions extracted
        """
        if not self._is_git_repository():
            raise RuntimeError("Current directory is not a git repository")

        commits = self._get_file_commits(filepath, after_date)

        if not commits:
            print(f"No commits found for file: {filepath}")
            return 0

        # Limit number of versions if specified
        if max_versions:
            commits = commits[:max_versions]

        extracted_count = 0
        previous_content = None

        for commit_hash, commit_date in commits:
            try:
                content = self._get_file_content_at_commit(filepath, commit_hash)

                # Skip if content is identical to previous version (metadata-only changes)
                if content == previous_content:
                    continue

                timestamp = self._format_timestamp(commit_date)
                output_path = self._generate_output_filename(filepath, timestamp)

                # Create directory if it doesn't exist
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Write file content
                output_path.write_text(content, encoding='utf-8')

                print(f"Extracted: {output_path} (commit: {commit_hash[:8]})")
                extracted_count += 1
                previous_content = content

            except RuntimeError as e:
                print(f"Warning: Could not extract version at commit {commit_hash[:8]}: {e}")
                continue

        return extracted_count


def main() -> None:
    """Main function to handle CLI arguments and execute file extraction."""
    parser = argparse.ArgumentParser(
        description="Extract different versions of a file from git history"
    )

    parser.add_argument(
        "filepath",
        help="Path to the file in the git repository"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show git commands being executed"
    )

    # Mutually exclusive group for filtering options
    filter_group = parser.add_mutually_exclusive_group()
    filter_group.add_argument(
        "--after-date",
        help="Extract versions after this date (YYYY-MM-DD format)"
    )
    filter_group.add_argument(
        "--max-versions",
        type=int,
        help="Maximum number of versions to extract (most recent first)"
    )

    args = parser.parse_args()

    try:
        extractor = GitFileExtractor(verbose=args.verbose)
        count = extractor.extract_versions(
            args.filepath,
            after_date=args.after_date,
            max_versions=args.max_versions
        )

        print(f"\nSuccessfully extracted {count} versions of '{args.filepath}'")

    except (RuntimeError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
