"""A plugin for reporting grades into a CSV file based on issue titles

.. module:: csvgrades
    :synopsis: A plugin for reporting grades into a CSV file based on issue
        titles

.. moduleauthor:: Simon Larsén
"""
import argparse
import pathlib
import configparser
import itertools

import daiquiri
import repobee_plug as plug

from repobee_csvgrades import _file
from repobee_csvgrades import _grades
from repobee_csvgrades import _marker
from repobee_csvgrades import _containers
from repobee_csvgrades import _exception

PLUGIN_NAME = "csvgrades"

LOGGER = daiquiri.getLogger(__file__)

grades_category = plug.cli.category(
    "grades",
    action_names=["record"],
    help="collect grading of students",
    description="Used to gather all student grades and save them insade a "
    "CSV file."
)


def callback(args: argparse.Namespace) -> None:
    results_file = args.hook_results_file
    grades_file = args.grades_file
    hook_results_mapping = _file.read_results_file(results_file)
    if "list-issues" not in hook_results_mapping:
        raise _exception.FileError(
            "can't locate list-issues metainfo in hook results"
        )
    if (
        not args.allow_other_states
        and plug.IssueState(
            hook_results_mapping["list-issues"][0].data["state"]
        )
        != plug.IssueState.ALL
    ):
        raise _exception.FileError(
            "repobee list-issues was not run with the --all flag. This may "
            "cause grading issues to be missed. Re-run list-issues with the "
            "--all flag, or run this command with --allow-other-states to "
            "record grades anyway."
        )

    grade_specs = list(
        map(_containers.GradeSpec.from_format, args.grade_specs)
    )
    grades = _grades.Grades(grades_file, args.assignments, grade_specs)
    grades.check_users(
        itertools.chain.from_iterable([t.members for t in args.students])
    )
    new_grades = _marker.mark_grades(
        grades,
        hook_results_mapping,
        args.students,
        args.assignments,
        args.teachers,
        grade_specs,
    )
    if new_grades:
        _file.write_edit_msg(
            sorted(new_grades.items()),
            args.assignments,
            pathlib.Path(args.edit_msg_file),
        )
        _file.write_grades_file(grades_file, grades)
    else:
        LOGGER.warning("No new grades reported")


class CSVGradeCommand(plug.Plugin, plug.cli.Command):

    __settings__ = plug.cli.command_settings(
        help="record grades from issues into a CSV file",
        description="Record grades from issues into a CSV file. Grade "
        "specifications on the form <PRIORITY>:<SYMBOL>:<REGEX> "
        "specify which issues are grading issues (by matching the title "
        "against the spec regex), and the corresponding symbol is written "
        "into the grades CSV file. If multiple grading issues are found "
        "in the same repo, the one with the lowest priority is recorded. "
        "A grade in the CSV file can only be overwritten by a grade with "
        "lower priority. Only grading issues opened by teachers "
        "specified by the ``--teachers`` option are recorded. Read more "
        "at https://github.com/slarse/repobee-csvgrades",
        action=grades_category.record,
        base_parsers=[
            plug.BaseParser.REPO_NAMES,
            plug.BaseParser.STUDENTS,
        ]
    )

    allow_other_states = plug.cli.flag(
        short_name="-a",
        help="Allow other list-issues states than 'all'. If this flag is "
        "not specified , the 'list-issues' command must have been run "
        "with the '--all' flag.",
        default=False,
    )
    teachers = plug.cli.option(
        short_name="--gs",
        help=(
            "One or more space-separated usernames of teachers/TAs "
            "that are authorized to open grading issues. If a "
            "grading issue is found by a user not in this list, "
            "a warning is logged and the grade is not recorded."
        ),
        argparse_kwargs={"nargs": "+"},
    )
    grade_specs = plug.cli.option(
        short_name="--gs",
        help=(
            "One or more grade specifications on the form "
            "<PRIORITY>:<SYMBOL>:<REGEX>. Example: 1:P:[Pp]ass"
        ),
        argparse_kwargs={"nargs": "+"},
    )
    edit_msg_file = plug.cli.option(
        short_name="--ef",
        help="filepath specifying where to put the edit message. "
        "Defaults to 'edit_msg.txt'",
        converter=pathlib.Path,
    )
    grades_file = plug.cli.option(
        short_name="--gf",
        help="path to the csv file with student grades",
        converter=pathlib.Path,
    )
    hook_results_file = plug.cli.option(
        short_name="--hf",
        help="path to an existing hook results file",
        converter=pathlib.Path,
    )

    def command(self):
        callback(self.args)

    def config_hook(self, config_parser: configparser.ConfigParser):
        self._hook_results_file = config_parser.get(
            PLUGIN_NAME, "hook_results_file", fallback=self._hook_results_file
        )
        self._grades_file = config_parser.get(
            PLUGIN_NAME, "grades_file", fallback=self._grades_file
        )
        self._edit_msg_file = config_parser.get(
            PLUGIN_NAME, "edit_msg_file", fallback=self._edit_msg_file
        )
        self._grade_specs = self._parse_grade_specs(config_parser)
        self._teachers = self._parse_teachers(config_parser)

    @staticmethod
    def _parse_teachers(config_parser):
        return [
            name.strip()
            for name in config_parser.get(
                PLUGIN_NAME, "teachers", fallback=""
            ).split(",")
        ]

    @staticmethod
    def _parse_grade_specs(config_parser):
        if not config_parser.has_section(PLUGIN_NAME):
            return []
        sec = config_parser[PLUGIN_NAME]
        return [
            value for key, value in sec.items() if key.endswith("gradespec")
        ]

def create_extension_command(self):
    parser = plug.ExtensionParser()
    parser.add_argument(
        "--hf",
        "--hook-results-file",
        help="Path to an existing hook results file.",
        type=str,
        required=not self._hook_results_file,
        default=self._hook_results_file,
        dest="hook_results_file",
    )
    parser.add_argument(
        "--gf",
        "--grades-file",
        help="Path to the CSV file with student grades.",
        type=str,
        required=not self._grades_file,
        default=self._grades_file,
        dest="grades_file",
    )
    parser.add_argument(
        "--ef",
        "--edit-msg-file",
        help="Filepath specifying where to put the edit message. "
        "Defaults to 'edit_msg.txt'",
        type=str,
        required=not self._edit_msg_file,
        default=self._edit_msg_file,
        dest="edit_msg_file",
    )
    parser.add_argument(
        "--gs",
        "--grade-specs",
        help=(
            "One or more grade specifications on the form "
            "<PRIORITY>:<SYMBOL>:<REGEX>. Example: 1:P:[Pp]ass"
        ),
        type=str,
        required=not self._grade_specs,
        default=self._grade_specs,
        nargs="+",
        dest="grade_specs",
    )
    parser.add_argument(
        "-t",
        "--teachers",
        help=(
            "One or more space-separated usernames of teachers/TAs "
            "that are authorized to open grading issues. If a "
            "grading issue is found by a user not in this list, "
            "a warning is logged and the grade is not recorded."
        ),
        type=str,
        required=not self._teachers,
        default=self._teachers,
        nargs="+",
    )
    parser.add_argument(
        "-a",
        "--allow-other-states",
        help="Allow other list-issues states than `all`. If this flag is "
        "not specified, the `list-issues` command must have been run "
        "with the `--all` flag.",
        action="store_true",
        default=False,
    )
    return plug.ExtensionCommand(
        parser=parser,
        name="record-grades",
        help="Record grades from issues into a CSV file.",
        description="Record grades from issues into a CSV file. Grade "
        "specifications on the form <PRIORITY>:<SYMBOL>:<REGEX> "
        "specify which issues are grading issues (by matching the title "
        "against the spec regex), and the corresponding symbol is written "
        "into the grades CSV file. If multiple grading issues are found "
        "in the same repo, the one with the lowest priority is recorded. "
        "A grade in the CSV file can only be overwritten by a grade with "
        "lower priority. Only grading issues opened by teachers "
        "specified by the ``--teachers`` option are recorded. Read more "
        "at https://github.com/slarse/repobee-csvgrades",
        callback=callback,
        requires_base_parsers=[
            plug.BaseParser.REPO_NAMES,
            plug.BaseParser.STUDENTS,
        ],
    )