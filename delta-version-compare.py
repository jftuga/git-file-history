#!/usr/bin/env python3

# Delta Version Compare Script
# This script interactively runs delta between consecutive versions of a file,
# starting with the newest versions. It discovers versioned files based on the
# timestamp naming convention and allows navigation through file history.

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def clear_screen() -> None:
    """
    Clear the terminal screen (cross-platform).
    """
    try:
        # Try to use termios (Unix/Linux/macOS)
        import termios
        import tty

        # Send clear screen escape sequence
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()
    except ImportError:
        # Fallback for Windows
        try:
            import msvcrt
            import os
            os.system('cls')
        except ImportError:
            # Ultimate fallback - print newlines
            print('\n' * 50)


def get_single_keypress() -> str:
    """
    Get a single keypress without requiring Enter (cross-platform).

    Returns:
        The pressed key as a string
    """
    try:
        # Try to use termios (Unix/Linux/macOS)
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return key
    except ImportError:
        # Fallback for Windows
        try:
            import msvcrt
            key = msvcrt.getch().decode('utf-8')
            return key
        except ImportError:
            # Ultimate fallback - requires Enter
            print("(Press Enter after your choice)")
            return input()


class DeltaVersionComparer:
    """Manages interactive delta comparisons between file versions."""

    def __init__(self, current_dir: Path = Path.cwd(), clear_screen_enabled: bool = False):
        """
        Initialize the comparer with a directory path.

        Args:
            current_dir: Directory to search for versioned files
            clear_screen_enabled: Whether to clear screen before each delta command
        """
        self.current_dir = current_dir
        self.clear_screen_enabled = clear_screen_enabled

    def _find_versioned_files(self, base_filename: str) -> list[Path]:
        """
        Find all versioned files for a given base filename.

        Args:
            base_filename: Base filename (e.g., 'popup.html')

        Returns:
            List of versioned file paths sorted by timestamp (newest first)
        """
        base_path = Path(base_filename)
        stem = base_path.stem
        suffix = base_path.suffix

        # Pattern: filename-YYYYmmdd.HHMMSS.ext
        pattern = re.compile(
            rf"^{re.escape(stem)}-(\d{{8}})\.(\d{{6}}){re.escape(suffix)}$"
        )

        versioned_files = []
        for file_path in self.current_dir.iterdir():
            if file_path.is_file():
                match = pattern.match(file_path.name)
                if match:
                    date_part, time_part = match.groups()
                    timestamp = f"{date_part}.{time_part}"
                    versioned_files.append((timestamp, file_path))

        # Sort by timestamp (newest first)
        versioned_files.sort(key=lambda x: x[0], reverse=True)
        return [file_path for _, file_path in versioned_files]

    def _run_delta(self, file1: Path, file2: Path) -> bool:
        """
        Run delta command between two files.

        Args:
            file1: First file path
            file2: Second file path

        Returns:
            True if delta command succeeded, False otherwise
        """
        try:
            subprocess.run(
                ["delta", str(file1), str(file2)],
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            # print(f"Error running delta: {e}", file=sys.stderr)
            return True
        except FileNotFoundError:
            print("Error: 'delta' command not found. Please install delta from https://github.com/dandavison/delta", file=sys.stderr)
            return False

    def _selective_compare(self, files_to_compare: list[Path]) -> bool:
        """
        Handle selective comparison between two user-chosen files.

        Args:
            files_to_compare: List of files available for comparison

        Returns:
            True if comparison was successful, False otherwise
        """
        print("\nAvailable files:")
        for i, file_path in enumerate(files_to_compare, 1):
            print(f"{i}) {file_path.name}")

        print(f"\nEnter two space-separated numbers (1-{len(files_to_compare)}) to compare:")
        try:
            user_input = input().strip()
            if not user_input:
                print("No input provided.")
                return False

            parts = user_input.split()
            if len(parts) != 2:
                print("Please enter exactly two numbers separated by a space.")
                return False

            try:
                num1, num2 = int(parts[0]), int(parts[1])
            except ValueError:
                print("Please enter valid numbers.")
                return False

            if num1 < 1 or num1 > len(files_to_compare) or num2 < 1 or num2 > len(files_to_compare):
                print(f"Numbers must be between 1 and {len(files_to_compare)}.")
                return False

            if num1 == num2:
                print("Please select two different files.")
                return False

            # Convert to 0-based indices
            file1 = files_to_compare[num1 - 1]
            file2 = files_to_compare[num2 - 1]

            print(f"\nComparing: {file1.name} -> {file2.name}")

            if self.clear_screen_enabled:
                clear_screen()

            return self._run_delta(file1, file2)

        except KeyboardInterrupt:
            print("\nSelective compare cancelled.")
            return False

    def _check_current_file_exists(self, filename: str) -> bool:
        """
        Check if the current file exists in the working directory.

        Args:
            filename: Name of the file to check

        Returns:
            True if file exists, False otherwise
        """
        return Path(filename).exists()

    def compare_versions(self, base_filename: str, include_current: bool = True) -> None:
        """
        Interactively compare file versions using delta.

        This method implements a controlled display loop using the show_current_comparison flag
        to manage when delta comparisons are automatically displayed versus when only the
        prompt appears. The flag ensures optimal user experience by:

        - Setting show_current_comparison=True for navigation commands (n, p, g, G) so users
          immediately see the new comparison they navigated to
        - Setting show_current_comparison=False after selective compare (s) so users get a
          clean prompt without forced re-display of their previous sequential position
        - Setting show_current_comparison=False after error messages to avoid redundant displays

        This design allows selective compare to feel like a non-disruptive side feature while
        maintaining the expected automatic display behavior for normal sequential navigation.
        Users retain full control - if they want to see the current comparison after selective
        compare, they can press any navigation key.

        Args:
            base_filename: Base filename to find versions for
            include_current: Whether to include current working file in comparison
        """
        versioned_files = self._find_versioned_files(base_filename)

        if not versioned_files:
            print(f"Error: No versioned files found for '{base_filename}'", file=sys.stderr)
            sys.exit(1)

        # Prepare file list for comparison
        files_to_compare = []

        if include_current and self._check_current_file_exists(base_filename):
            files_to_compare.append(Path(base_filename))
            print(f"Including current file: {base_filename}")

        files_to_compare.extend(versioned_files)

        if len(files_to_compare) < 2:
            print("Error: Need at least 2 files to compare", file=sys.stderr)
            sys.exit(1)

        print(f"Found {len(files_to_compare)} files to compare")
        print("Controls: 'n' for next, 'p' for previous, 's' for selective compare, 'g' for beginning, 'G' for end, 'q' to quit")
        print()

        current_index = 0
        max_index = len(files_to_compare) - 2  # Last valid comparison index
        show_current_comparison = True  # Flag to control when to display current comparison

        while True:
            if current_index > max_index:
                print("\nReached the end of file history.")
                break

            # Only show current comparison when flag is True
            if show_current_comparison:
                file1 = files_to_compare[current_index]
                file2 = files_to_compare[current_index + 1]

                print(f"Comparing: {file1.name} -> {file2.name}")

                if self.clear_screen_enabled:
                    clear_screen()

                if not self._run_delta(file1, file2):
                    print("Failed to run delta comparison")
                    break

            # Prepare prompt based on current position
            position_info = f"({current_index + 1}/{max_index + 1})"

            if current_index == 0 and current_index == max_index:
                # Only one comparison available
                prompt = f"\nPress 's' for selective compare {position_info}, or 'q' to quit: "
                valid_keys = {'s', 'q'}
            elif current_index == 0:
                # First comparison - no previous option
                prompt = f"\nPress 'n' for next, 's' for selective compare, 'G' for end {position_info}, or 'q' to quit: "
                valid_keys = {'n', 's', 'G', 'q'}
            elif current_index == max_index:
                # Last comparison - no next option
                prompt = f"\nPress 'p' for previous, 's' for selective compare, 'g' for beginning {position_info}, or 'q' to quit: "
                valid_keys = {'p', 's', 'g', 'q'}
            else:
                # Middle comparisons - all options available
                prompt = f"\nPress 'n' for next, 'p' for previous, 's' for selective compare, 'g' for beginning, 'G' for end {position_info}, or 'q' to quit: "
                valid_keys = {'n', 'p', 's', 'g', 'G', 'q'}

            print(prompt, end="", flush=True)

            key = get_single_keypress()
            print(key)  # Echo the key for user feedback

            if key == 'q':
                print("Exiting...")
                break
            elif key == 's':
                print("Selective compare")
                if self._selective_compare(files_to_compare):
                    print()  # Add spacing after selective compare
                else:
                    print("Selective compare failed or cancelled.")
                    print()
                show_current_comparison = False  # Skip auto-display after selective compare
            elif key == 'n' and current_index < max_index:
                current_index += 1
                show_current_comparison = True  # Show comparison for navigation
                print()
            elif key == 'p' and current_index > 0:
                current_index -= 1
                show_current_comparison = True  # Show comparison for navigation
                print()
            elif key == 'g':
                if current_index != 0:
                    current_index = 0
                    show_current_comparison = True  # Show comparison for navigation
                    print("Jumped to beginning")
                    print()
                else:
                    print("Already at the beginning.")
                    show_current_comparison = False  # Don't re-display if already there
            elif key == 'G':
                if current_index != max_index:
                    current_index = max_index
                    show_current_comparison = True  # Show comparison for navigation
                    print("Jumped to end")
                    print()
                else:
                    print("Already at the end.")
                    show_current_comparison = False  # Don't re-display if already there
            else:
                # Invalid input handling
                if key not in valid_keys:
                    if current_index == 0 and current_index == max_index:
                        print("Invalid input. Use 's' for selective compare or 'q' to quit.")
                    elif current_index == 0:
                        print("Invalid input. Use 'n' for next, 's' for selective compare, 'G' for end, or 'q' to quit.")
                    elif current_index == max_index:
                        print("Invalid input. Use 'p' for previous, 's' for selective compare, 'g' for beginning, or 'q' to quit.")
                    else:
                        print("Invalid input. Use 'n' for next, 'p' for previous, 's' for selective compare, 'g' for beginning, 'G' for end, or 'q' to quit.")
                else:
                    # Handle boundary cases
                    if key == 'n':
                        print("Cannot go to next from the last comparison.")
                    elif key == 'p':
                        print("Cannot go to previous from the first comparison.")
                show_current_comparison = False  # Don't re-display after error messages


def main() -> None:
    """Main function to handle CLI arguments and execute version comparison."""
    parser = argparse.ArgumentParser(
        description="Interactively compare file versions using delta"
    )

    parser.add_argument(
        "filename",
        help="Base filename to find versions for (e.g., 'popup.html')"
    )

    parser.add_argument(
        "-c", "--clear",
        action="store_true",
        help="Clear screen before displaying each delta comparison"
    )

    parser.add_argument(
        "-n", "--no-current",
        action="store_true",
        help="Don't include the current working file in comparison"
    )

    args = parser.parse_args()

    try:
        comparer = DeltaVersionComparer(clear_screen_enabled=args.clear)
        comparer.compare_versions(
            args.filename,
            include_current=not args.no_current
        )
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()