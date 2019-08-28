"""Class for managing a grades CSV file."""
import pathlib
import sys

from typing import List, Iterable

from repobee_csvgrades import _file
from repobee_csvgrades import _containers
from repobee_csvgrades import _exception


class Grades:
    """Abstraction of the grades file."""

    def __init__(
        self,
        grades_file: pathlib.Path,
        master_repo_names: List[str],
        grade_specs: List[_containers.GradeSpec],
    ):
        self._headers, self._contents = _file.read_grades_file(grades_file)
        self._symbol_to_spec = {spec.symbol: spec for spec in grade_specs}
        self._symbol_to_spec[""] = _containers.GradeSpec(
            symbol="", priority=sys.maxsize, regex=""
        )
        self._usr_to_row, self._repo_to_col = extract_row_and_col_mappings(
            self._headers, self._contents, master_repo_names
        )
        self._original_contents = self._contents

    def __getitem__(self, key):
        usr, repo = key
        row = self._usr_to_row[usr]
        col = self._repo_to_col[repo]
        return self._contents[row][col]

    def __setitem__(self, key, value):
        usr, repo = key
        row = self._usr_to_row[usr]
        col = self._repo_to_col[repo]
        self._contents[row][col] = value

    def set(self, usr, repo, value) -> str:
        old = self[usr, repo]
        try:
            old_spec = self._symbol_to_spec[old]
        except KeyError as exc:
            raise _exception.FileError(
                "grades file contains unknown grade symbol {}".format(old)
            ) from exc
        if old_spec.priority < value.priority:
            raise _exception.GradingError("try to set higher priority grade")
        self[usr, repo] = value.symbol
        return old_spec

    def check_users(self, usernames: Iterable[str]) -> bool:
        missing_users = set(usernames) - set(self._usr_to_row.keys())
        if missing_users:
            raise _exception.FileError(
                "student(s) {} missing from the grades file".format(
                    ", ".join(sorted(missing_users))
                )
            )

    @property
    def csv(self):
        output_contents = [self._headers, *self._contents]
        column_widths = largest_cells(output_contents)
        return [
            [cell.rjust(column_widths[i]) for i, cell in enumerate(row)]
            for row in output_contents
        ]


def extract_row_and_col_mappings(
    grades_headers, grades_file_contents, master_repo_names
):
    """Extract mappings from username -> row_nr and master_repo_name ->
    col_nr.
    """
    master_repo_to_col_nr = {
        repo_name: grades_headers.index(repo_name)
        for repo_name in master_repo_names
    }
    username_col = grades_headers.index("username")
    username_to_row_nr = {
        row[username_col]: i for i, row in enumerate(grades_file_contents)
    }
    return username_to_row_nr, master_repo_to_col_nr


def largest_cells(rows):
    """Return a list with the widths of the largest cell of each column."""
    transpose = list(zip(*rows))
    widths = map(lambda row: map(len, row), transpose)
    return list(map(max, widths))
