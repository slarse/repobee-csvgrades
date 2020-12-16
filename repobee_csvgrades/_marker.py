"""Utility functions for marking grades.

.. module:: _marker
    :synopsis: Utility functions for marking grades.

.. moduleauthor:: Simon Larsén
"""
import collections
import itertools
import re
import heapq
import contextlib
import dataclasses
from typing import List

import daiquiri

import repobee_plug as plug

from repobee_csvgrades import _exception
from repobee_csvgrades import _containers

LOGGER = daiquiri.getLogger(__file__)

@dataclasses.dataclass(frozen=True, order=True)
class _SpeccedIssue:
    """Wrapper for an issue and associated grade spec, which is ordered by the
    gradespec.
    """

    spec: _containers.GradeSpec = dataclasses.field(compare=True)
    issue: plug.platform.Issue = dataclasses.field(compare=False)

def get_authorized_issues(issues, teachers, grade_spec, repo_name):
    matched_issues = [
        issue for issue in issues if re.match(grade_spec.regex, issue.title)
    ]
    authorized = [
        issue for issue in matched_issues if issue.author in teachers
    ]
    unauthorized = [
        issue for issue in matched_issues if issue.author not in teachers
    ]
    if unauthorized:
        for issue in unauthorized:
            LOGGER.warning(
                "Grading issue {}#{} by unauthorized user {}".format(
                    repo_name, issue.number, issue.author
                )
            )
    return authorized


def mark_grade(
    grades, team, master_repo_name, hook_results_mapping, teachers, grade_specs
):
    repo_name = generate_repo_name(str(team), master_repo_name)
    if repo_name not in hook_results_mapping:
        LOGGER.warning(
            "hook results for {} missing from JSON file".format(repo_name)
        )
        return None, None, None
    list_issues_result = extract_list_issues_results(
        repo_name, hook_results_mapping[repo_name]
    )
    issues = [
        plug.Issue.from_dict(issue_dict)
        for issue_dict in list_issues_result.data.values()
    ]

    issue_heap = []
    for spec in grade_specs:
        for issue in get_authorized_issues(issues, teachers, spec, repo_name):
            heapq.heappush(issue_heap, _SpeccedIssue(spec, issue))

    graded_students = []
    author = None
    symbol = None
    if issue_heap:
        spec, issue = issue_heap[0].spec, issue_heap[0].issue
        for student in team.members:
            with log_error(_exception.GradingError):
                old = grades.set(student, master_repo_name, spec)
                if old != spec:
                    graded_students.append(student)
                    LOGGER.info(
                        "{} for {} on {}".format(
                            spec.symbol, student, master_repo_name
                        )
                    )
                    author = issue.author
                    symbol = spec.symbol

    return graded_students, symbol, author


def mark_grades(
    grades,
    hook_results_mapping,
    teams,
    master_repo_names,
    teachers,
    grade_specs,
):
    new_grades = collections.defaultdict(list)

    for team, master_repo_name in itertools.product(teams, master_repo_names):
        graded_students, grade, author = mark_grade(
            grades,
            team,
            master_repo_name,
            hook_results_mapping,
            teachers,
            grade_specs,
        )
        if graded_students:
            new_grades[author] += [
                (student, master_repo_name, grade)
                for student in graded_students
            ]

    return new_grades


def extract_list_issues_results(
    repo_name, hook_results: List[plug.Result]
) -> plug.Result:
    for result in hook_results:
        if result.name == "list-issues":
            return result
    raise plug.PlugError(
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


@contextlib.contextmanager
def log_error(*errors):
    try:
        yield
    except errors as exc:
        LOGGER.warning(str(exc))
