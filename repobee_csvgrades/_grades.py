"""Class for managing a grades CSV file."""

import pathlib

from typing import List

from repobee_csvgrades import _file


class Grades:
    """Abstraction of the grades file."""

    def __init__(
        self, grades_file: pathlib.Path, master_repo_names: List[str]
    ):
        self._headers, self._contents = _file.read_grades_file(grades_file)
        self._original_contents = self._contents
        self._usr_to_row, self._repo_to_col = extract_row_and_col_mappings(
            self._headers, self._contents, master_repo_names
        )

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
        self[usr, repo] = value
        return old

    @property
    def csv(self):
        return [self._headers, *self._contents]


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
