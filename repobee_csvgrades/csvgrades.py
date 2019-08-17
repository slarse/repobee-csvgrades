"""A plugin for reporting grades into a CSV file based on issue titles

.. module:: csvgrades
    :synopsis: A plugin for reporting grades into a CSV file based on issue titles

.. moduleauthor:: Simon Larsén
"""
import argparse
import pathlib
import daiquiri

import repobee_plug as plug

from repobee_csvgrades import _file
from repobee_csvgrades import _grades
from repobee_csvgrades import _marker
from repobee_csvgrades import _containers

PLUGIN_NAME = "csvgrades"

LOGGER = daiquiri.getLogger(__file__)


def callback(args: argparse.Namespace, api: None) -> None:
    results_file = pathlib.Path(args.hook_results_file)
    grades_file = pathlib.Path(args.grades_file)
    hook_results_mapping = _file.read_results_file(results_file)
    grade_specs = list(
        map(_containers.GradeSpec.from_format, args.grade_specs)
    )
    grades = _grades.Grades(grades_file, args.master_repo_names, grade_specs)
    new_grades = _marker.mark_grades(
        grades,
        hook_results_mapping,
        args.students,
        args.master_repo_names,
        args.teachers,
        grade_specs,
    )
    if new_grades:
        _file.write_edit_msg(
            new_grades,
            args.master_repo_names,
            pathlib.Path(args.edit_msg_file),
        )
        _file.write_grades_file(grades_file, grades)
    else:
        LOGGER.warning("No new grades reported")


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
    parser.add_argument(
        "--edit-msg-file",
        help="Filepath specifying where to put the edit message. "
        "Defaults to 'edit_msg.txt'",
        type=str,
        default="edit_msg.txt",
    )
    parser.add_argument(
        "--gs",
        "--grade-specs",
        help="One or more grade specifications on the form <PRIORITY>:<SYMBOL>:<REGEX>",
        required=True,
        type=str,
        nargs="+",
        dest="grade_specs",
    )
    parser.add_argument(
        "-t",
        "--teachers",
        help="One or more space-separated usernames of teachers/TAs that are "
        "authorized to open grading issues. If a grading issue is found by a "
        "user not in this list, a warning is issued and the grade is not "
        "recorded.",
        required=True,
        nargs="+",
        type=str,
    )
    return plug.ExtensionCommand(
        parser=parser,
        name="csvgrades",
        help="Blabla",
        description="More blaba",
        callback=callback,
        requires_base_parsers=[
            plug.BaseParser.REPO_NAMES,
            plug.BaseParser.STUDENTS,
        ],
    )
