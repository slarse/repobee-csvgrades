"""Utility functions for marking grades.

.. module:: _marker
    :synopsis: Utility functions for marking grades.

.. moduleauthor:: Simon Larsén
"""
import collections
import itertools
from typing import List

import daiquiri

import repobee_plug as plug

LOGGER = daiquiri.getLogger(__file__)


def mark_grade(grades, team, master_repo_name, hook_results_mapping, teachers):
    repo_name = generate_repo_name(str(team), master_repo_name)
    list_issues_result = extract_list_issues_results(
        repo_name, hook_results_mapping[repo_name]
    )
    issues = (
        plug.Issue.from_dict(issue_dict)
        for issue_dict in list_issues_result.data.values()
    )
    pass_issues = [issue for issue in issues if issue.title == "Pass"]
    authorized = [issue for issue in pass_issues if issue.author in teachers]
    unauthorized = [
        issue for issue in pass_issues if issue.author not in teachers
    ]

    if unauthorized:
        for issue in unauthorized:
            LOGGER.warning(
                "Grading issue {}#{} by unauthorized user {}".format(
                    repo_name, issue.number, issue.author
                )
            )

    graded_students = []
    grade = "P"
    author = None
    if authorized:
        issue = authorized[0]
        author = issue.author
        for student in team.members:
            old = grades.set(student, master_repo_name, grade)
            if old != grade:
                graded_students.append(student)
                LOGGER.info(
                    "{} for {} on {}".format(grade, student, master_repo_name)
                )

    return graded_students, grade, author


def mark_grades(
    grades, hook_results_mapping, teams, master_repo_names, teachers
):
    new_grades = collections.defaultdict(list)

    for team, master_repo_name in itertools.product(teams, master_repo_names):
        graded_students, grade, author = mark_grade(
            grades, team, master_repo_name, hook_results_mapping, teachers
        )
        if graded_students:
            new_grades[author] += [
                (student, master_repo_name, grade)
                for student in graded_students
            ]

    return new_grades


def extract_list_issues_results(
    repo_name, hook_results: List[plug.HookResult]
) -> plug.HookResult:
    for result in hook_results:
        if result.hook == "list-issues":
            return result
    raise plug.exception.PlugError(
        "hook results for {} does not contain 'list-issues' result".format(
            repo_name
        )
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
