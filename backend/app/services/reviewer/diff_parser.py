import re
from typing import List, Dict, Any, Set


class DiffHunk:
    def __init__(self, old_start: int, old_len: int, new_start: int, new_len: int, lines: List[str]):
        self.old_start = old_start
        self.old_len = old_len
        self.new_start = new_start
        self.new_len = new_len
        self.lines = lines

    @property
    def target_start(self) -> int:
        return self.new_start

    @property
    def target_length(self) -> int:
        return self.new_len

    @property
    def source_start(self) -> int:
        return self.old_start

    @property
    def source_length(self) -> int:
        return self.old_len


class FileDiff:
    def __init__(self, file_path: str, is_new: bool, is_deleted: bool, hunks: List[DiffHunk], modified_lines: Set[int]):
        self.file_path = file_path
        self.is_new = is_new
        self.is_deleted = is_deleted
        self.hunks = hunks
        self.modified_lines = modified_lines


def parse_unified_diff(diff_text: str) -> List[FileDiff]:
    """
    Parses git unified diff string into structured file diffs and changed line numbers.
    """
    file_diffs: List[FileDiff] = []
    lines = diff_text.splitlines()
    
    current_file = None
    current_hunks = []
    current_modified_lines = set()
    is_new = False
    is_deleted = False

    hunk_header_re = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("diff --git"):
            # Save previous file diff
            if current_file:
                file_diffs.append(
                    FileDiff(
                        file_path=current_file,
                        is_new=is_new,
                        is_deleted=is_deleted,
                        hunks=current_hunks,
                        modified_lines=current_modified_lines
                    )
                )
            
            # Extract target file name
            parts = line.split()
            if len(parts) >= 4:
                b_path = parts[3]
                current_file = b_path[2:] if b_path.startswith("b/") else b_path
            else:
                current_file = "unknown"
            
            current_hunks = []
            current_modified_lines = set()
            is_new = False
            is_deleted = False
            i += 1
            continue

        if line.startswith("new file mode"):
            is_new = True
            i += 1
            continue
        elif line.startswith("deleted file mode"):
            is_deleted = True
            i += 1
            continue

        m = hunk_header_re.match(line)
        if m:
            old_start = int(m.group(1))
            old_len = int(m.group(2)) if m.group(2) else 1
            new_start = int(m.group(3))
            new_len = int(m.group(4)) if m.group(4) else 1

            hunk_lines = []
            i += 1
            curr_new_line = new_start

            while i < len(lines) and not lines[i].startswith("diff --git") and not hunk_header_re.match(lines[i]):
                hunk_line = lines[i]
                hunk_lines.append(hunk_line)
                if hunk_line.startswith("+"):
                    current_modified_lines.add(curr_new_line)
                    curr_new_line += 1
                elif hunk_line.startswith(" "):
                    curr_new_line += 1
                i += 1

            current_hunks.append(DiffHunk(old_start, old_len, new_start, new_len, hunk_lines))
            continue

        i += 1

    if current_file:
        file_diffs.append(
            FileDiff(
                file_path=current_file,
                is_new=is_new,
                is_deleted=is_deleted,
                hunks=current_hunks,
                modified_lines=current_modified_lines
            )
        )

    return file_diffs
