"""Write your plugin in here!

This module comes with two example implementations of a hook, one wrapped in
a class and one as a standalone hook function.

.. module:: csvgrades
    :synopsis: A plugin for reporting grades into a CSV file based on issue titles

.. moduleauthor:: Simon Larsén
"""
import sys
import argparse
import csv
import pathlib
import itertools

from typing import List

# this import you'll need
import repobee_plug as plug

PLUGIN_NAME = "csvgrades"


def callback(args: argparse.Namespace, api: None) -> None:
    results_file = pathlib.Path(args.hook_results_file)
    hook_results_mapping = read_results_file(results_file)
    grades_file = pathlib.Path(args.grades_file)
    grades_headers, grades_file_contents = read_grades_file(grades_file)
    marked_grades = mark_grades(
        grades_headers,
        grades_file_contents,
        hook_results_mapping,
        args.students,
        args.master_repo_names,
    )
    write_grades_file(grades_file, grades_headers, marked_grades)


def mark_grades(
    grades_headers, grades_file_contents, hook_results_mapping, teams, master_repo_names
):
    grades_file_contents = [list(row) for row in grades_file_contents]  # safe copy
    master_repo_name_to_column_nr = {
        repo_name: grades_headers.index(repo_name) for repo_name in master_repo_names
    }
    username_column = grades_headers.index("username")
    username_to_row_nr = {
        row[username_column]: i for i, row in enumerate(grades_file_contents)
    }

    for team, master_repo_name in itertools.product(teams, master_repo_names):
        repo_name = generate_repo_name(str(team), master_repo_name)
        list_issues_result = extract_list_issues_results(
            repo_name, hook_results_mapping[repo_name]
        )
        issues = (
            plug.Issue.from_dict(issue_dict)
            for issue_dict in list_issues_result.data.values()
        )
        pass_issues = [issue for issue in issues if issue.title == "Pass"]
        if pass_issues:
            for student in team.members:
                col = master_repo_name_to_column_nr[master_repo_name]
                row = username_to_row_nr[student]
                grade = "P"
                old = mark(grades_file_contents, row, col, grade)
                if old != grade:
                    print("{} for {} on {}".format(grade, student, master_repo_name))

    return grades_file_contents


def mark(grades_file_contents, row, col, grade) -> str:
    """Mark with the new grade and return the old grade."""
    old = grades_file_contents[row][col]
    grades_file_contents[row][col] = grade
    return old


def write_grades_file(grades_file, headers, content):
    with open(str(grades_file), mode="w", encoding=sys.getdefaultencoding()) as dst:
        writer = csv.writer(dst, delimiter=",")
        writer.writerows([headers, *content])


def read_results_file(results_file):
    if not results_file.is_file():
        raise plug.PlugError("no such file: {}".format(str(results_file)))
    return plug.json_to_result_mapping(
        results_file.read_text(encoding=sys.getdefaultencoding())
    )


def read_grades_file(grades_file):
    if not grades_file.is_file():
        raise plug.PlugError("no such file: {}".format(str(grades_file)))
    with open(str(grades_file), encoding=sys.getdefaultencoding(), mode="r") as file:
        grades_file_contents = [
            [cell.strip() for cell in row] for row in csv.reader(file, delimiter=",")
        ]
        return grades_file_contents[0], grades_file_contents[1:]


def extract_list_issues_results(
    repo_name, hook_results: List[plug.HookResult]
) -> plug.HookResult:
    for result in hook_results:
        if result.hook == "list-issues":
            return result
    raise plug.exception.PlugError(
        "hook results for {} does not contain 'list-issues' result".format(repo_name)
    )


# TODO Generation functions duplicated from repobee, function should be moved
# to repobee-plug
def generate_repo_name(team_name: str, master_repo_name: str) -> str:
    """Construct a repo name for a team.

    Args:
        team_name: Name of the associated team.
        master_repo_name: Name of the template repository.
    """
    return "{}-{}".format(team_name, master_repo_name)


def generate_repo_names(
    team_names: List[str], master_repo_names: List[str]
) -> List[str]:
    """Construct all combinations of generate_repo_name(team_name,
    master_repo_name) for the provided team names and master repo names.

    Args:
        team_names: One or more names of teams.
        master_repo_names: One or more names of master repositories.

    Returns:
        a list of repo names for all combinations of team and master repo.
    """
    return [
        generate_repo_name(team_name, master_name)
        for master_name in master_repo_names
        for team_name in team_names
    ]


@plug.repobee_hook
def create_extension_command():
    parser = plug.ExtensionParser()
    parser.add_argument(
        "--hook-results-file",
        help="Path to an existing hook results file.",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--grades-file",
        help="Path to the CSV file with student grades.",
        type=str,
        required=True,
    )
    return plug.ExtensionCommand(
        parser=parser,
        name="csvgrades",
        help="Blabla",
        description="More blaba",
        callback=callback,
        requires_base_parsers=[plug.BaseParser.REPO_NAMES, plug.BaseParser.STUDENTS],
    )
