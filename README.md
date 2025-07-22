# git-file-history

A collection of Python tools for extracting and comparing different
versions of files from git repository history. These scripts make
it easy to analyze how files have evolved over time by extracting
historical versions and providing interactive diff comparisons.

## Overview

This project consists of two complementary scripts:

- **`git-version-extractor.py`** - Extracts different versions of a file from git history, saving each version with timestamp-based filenames
- **`delta-compare.py`** - Provides interactive comparison of file versions using the delta diff tool

Both tools work together to provide a complete workflow for analyzing file evolution in git repositories.

## Requirements

- Python 3.12+
- Git repository
- [delta](https://github.com/dandavison/delta) (for diff comparisons)

## Installation

Clone this repository:

```bash
git clone https://github.com/jftuga/git-file-history.git
cd git-file-history
```

Install delta (required for `delta-compare.py`):

```bash
# macOS
brew install git-delta

# Ubuntu/Debian

# change to most current version...
wget https://github.com/dandavison/delta/releases/download/0.18.2/git-delta_0.18.2_amd64.deb
sudo dpkg -i git-delta_0.18.2_amd64.deb

# Other platforms: see https://dandavison.github.io/delta/installation.html
```

## Usage

### git-version-extractor.py

Extracts historical versions of a file from git history.

```bash
python git-version-extractor.py [OPTIONS] FILEPATH
```

**Options:**
- `--after-date YYYY-MM-DD` - Extract versions after specified date
- `--max-versions N` - Limit to N most recent versions
- `-v, --verbose` - Show git commands being executed

**Output Format:**
Files are saved with timestamp-based names: `filename-YYYYmmdd.HHMMSS.ext`

### delta-compare.py

Interactive comparison of file versions using delta.

```bash
python delta-compare.py [OPTIONS] FILENAME
```

**Options:**
- `-c, --clear` - Clear screen before each delta comparison
- `--no-current` - Don't include current working file in comparison

**Interactive Controls:**
- `n` - Next comparison (toward older versions)
- `p` - Previous comparison (toward newer versions)
- `q` - Quit

## Examples

### Basic File Extraction

Extract all versions of a configuration file:

```bash
python git-version-extractor.py config/settings.json
```

Output:
```
Extracted: config/settings-20250722.143022.json (commit: abc12345)
Extracted: config/settings-20250715.091503.json (commit: def67890)
Extracted: config/settings-20250708.165432.json (commit: ghi11121)

Successfully extracted 3 versions of 'config/settings.json'
```

### Date-Filtered Extraction

Extract versions from the last month:

```bash
python git-version-extractor.py src/main.py --after-date 2025-06-22
```

### Limited Version Extraction

Get only the 5 most recent versions:

```bash
python git-version-extractor.py README.md --max-versions 5
```

### Verbose Extraction

See git commands being executed:

```bash
python git-version-extractor.py -v package.json --max-versions 3
```

Output:
```
Running: git rev-parse --git-dir
Running: git log --pretty=format:%H|%ci --max-count=3 --follow package.json
Running: git show a1b2c3d4:package.json
Extracted: package-20250722.143022.json (commit: a1b2c3d4)
```

### Interactive File Comparison

Compare all versions of a file including current working version:

```bash
python delta-compare.py popup.html
```

Interactive session:
```
Found 4 files to compare
Controls: 'n' for next, 'p' for previous, 'q' to quit

Comparing: popup.html -> popup-20250722.010203.html
Running delta...
[delta diff output appears here]

Press 'n' for next comparison (1/3) or 'q' to quit: n

Comparing: popup-20250722.010203.html -> popup-20250721.143022.html
Running delta...
[delta diff output appears here]

Press 'n' for next, 'p' for previous (2/3), or 'q' to quit: p
```

### Clean Screen Comparisons

Clear screen before each diff for focused viewing:

```bash
python delta-compare.py -c src/lambda/index.py
```

### Compare Only Historical Versions

Exclude current working file from comparison:

```bash
python delta-compare.py --no-current config.yml
```

## Typical Workflow

1. **Extract versions** of a file you want to analyze:
   ```bash
   python git-version-extractor.py src/app.py --max-versions 10
   ```

2. **Compare versions** interactively:
   ```bash
   python delta-compare.py -c src/app.py
   ```

3. Navigate through the history using `n` (next) and `p` (previous) to understand how the file evolved over time.

## File Naming Convention

Extracted files use the format: `{filename}-{YYYYmmdd.HHMMSS}.{extension}`

Examples:
- `index.html` -> `index-20250722.143022.html`
- `main.py` -> `main-20250715.091503.py`
- `config.json` -> `config-20250708.165432.json`

The timestamp represents the commit date/time in the commit's original timezone.

