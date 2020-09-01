import pathlib
import argparse
import shutil
from datetime import datetime
from unittest import mock

import pytest

import repobee_plug as plug
from _repobee import plugin

from repobee_csvgrades import csvgrades
from repobee_csvgrades import _file
from repobee_csvgrades import _marker
from repobee_csvgrades import _exception

TEAMS = tuple(
    [
        plug.StudentTeam(members=members)
        for members in (["slarse"], ["glassey", "glennol"])
    ]
)
DIR = pathlib.Path(__file__).parent
GRADES_FILE = DIR / "grades.csv"
EXPECTED_GRADES_FILE = DIR / "expected_grades.csv"
EXPECTED_GRADES_MULTI_SPEC_FILE = DIR / "expected_grades_multi_spec.csv"
EXPECTED_EDIT_MSG_FILE = DIR / "expected_edit_msg.txt"
EXPECTED_EDIT_MSG_MULTI_SPEC_FILE = DIR / "expected_edit_msg_multi_spec.txt"

SLARSE_TA = "ta_a"
GLASSEY_GLENNOL_TA = "ta_b"
TEACHERS = (SLARSE_TA, GLASSEY_GLENNOL_TA)

PASS_GRADESPEC_FORMAT = "1:P:[Pp]ass"
FAIL_GRADESPEC_FORMAT = "2:F:[Ff]ail"
KOMP_GRADESPEC_FORMAT = "3:K:[Kk]omplettering"


def create_pass_hookresult(author):
    pass_issue = plug.Issue(
        title="Pass",
        body="This is a pass",
        number=3,
        created_at=datetime(1992, 9, 19),
        author=author,
    )
    return plug.Result(
        name="list-issues",
        status=plug.Status.SUCCESS,
        msg=None,
        data={pass_issue.number: pass_issue.to_dict()},
    )


def create_komp_hookresult(author):
    komp_issue = plug.Issue(
        title="Komplettering",
        body="This is komplettering",
        number=1,
        created_at=datetime(2009, 12, 31),
        author=author,
    )
    return plug.Result(
        name="list-issues",
        status=plug.Status.SUCCESS,
        msg=None,
        data={komp_issue.number: komp_issue.to_dict()},
    )


def create_komp_and_pass_hookresult(author):
    other = create_komp_hookresult(author)
    pass_ = create_pass_hookresult(author)
    return plug.Result(
        name="list-issues",
        status=plug.Status.SUCCESS,
        msg=None,
        data={**other.data, **pass_.data},
    )


@pytest.fixture
def mocked_hook_results(mocker):
    """Hook results with passes for glassey-glennol in week-1 and week-2, and
    for slarse in week-4 and week-6.
    """
    slarse, glassey_glennol = TEAMS
    gen_name = _marker.generate_repo_name
    hook_results = {
        gen_name(str(team), repo_name): [result]
        for team, repo_name, result in [
            (slarse, "week-1", create_komp_hookresult(SLARSE_TA)),
            (slarse, "week-2", create_komp_hookresult(SLARSE_TA)),
            (slarse, "week-4", create_pass_hookresult(SLARSE_TA)),
            (slarse, "week-6", create_komp_and_pass_hookresult(SLARSE_TA)),
            (
                glassey_glennol,
                "week-1",
                create_pass_hookresult(GLASSEY_GLENNOL_TA),
            ),
            (
                glassey_glennol,
                "week-2",
                create_komp_and_pass_hookresult(GLASSEY_GLENNOL_TA),
            ),
            (
                glassey_glennol,
                "week-4",
                create_komp_hookresult(GLASSEY_GLENNOL_TA),
            ),
            (
                glassey_glennol,
                "week-6",
                create_komp_hookresult(GLASSEY_GLENNOL_TA),
            ),
        ]
    }
    hook_results["list-issues"] = [
        plug.Result(
            name="list-issues",
            status=plug.Status.SUCCESS,
            msg=None,
            data={"state": plug.IssueState.ALL.value},
        )
    ]
    mocker.patch(
        "repobee_csvgrades._file.read_results_file",
        return_value=hook_results,
        autospec=True,
    )
    return hook_results


@pytest.fixture
def tmp_grades_file(tmpdir):
    grades_file = pathlib.Path(str(tmpdir)) / "grades.csv"
    shutil.copy(str(GRADES_FILE), str(grades_file))
    yield grades_file


class TestCallback:
    def test_correctly_marks_passes(
        self, tmp_grades_file, mocked_hook_results
    ):
        args = argparse.Namespace(
            students=list(TEAMS),
            hook_results_file="",  # don't care, read_results_file is mocked
            grades_file=tmp_grades_file,
            assignments="week-1 week-2 week-4 week-6".split(),
            edit_msg_file=str(tmp_grades_file.parent / "editmsg.txt"),
            teachers=list(TEACHERS),
            grade_specs=[PASS_GRADESPEC_FORMAT],
            allow_other_states=False,
        )

        csvgrades.callback(args=args)

        assert _file.read_grades_file(
            tmp_grades_file
        ) == _file.read_grades_file(EXPECTED_GRADES_FILE)

    def test_writes_edit_msg(
        self, tmp_grades_file, mocked_hook_results, mocker
    ):
        edit_msg_file = tmp_grades_file.parent / "editmsg.txt"
        args = argparse.Namespace(
            students=list(TEAMS),
            hook_results_file="",  # don't care, read_results_file is mocked
            grades_file=tmp_grades_file,
            assignments="week-1 week-2 week-4 week-6".split(),
            edit_msg_file=str(edit_msg_file),
            teachers=list(TEACHERS),
            grade_specs=[PASS_GRADESPEC_FORMAT],
            allow_other_states=False,
        )

        csvgrades.callback(args=args)

        assert (
            edit_msg_file.read_text("utf8").strip()
            == EXPECTED_EDIT_MSG_FILE.read_text("utf8").strip()
        )

    def test_writes_nothing_if_graders_are_not_teachers(
        self, tmp_grades_file, mocked_hook_results
    ):
        edit_msg_file = tmp_grades_file.parent / "editmsg.txt"
        grades_file_contents = tmp_grades_file.read_text(encoding="utf8")
        args = argparse.Namespace(
            students=list(TEAMS),
            hook_results_file="",  # don't care, read_results_file is mocked
            grades_file=tmp_grades_file,
            assignments="week-1 week-2 week-4 week-6".split(),
            edit_msg_file=str(edit_msg_file),
            teachers=["glassey", "slarse"],  # wrong teachers!
            grade_specs=[PASS_GRADESPEC_FORMAT],
            allow_other_states=False,
        )

        csvgrades.callback(args=args)

        assert tmp_grades_file.read_text("utf8") == grades_file_contents
        assert not edit_msg_file.exists()

    def test_multiple_specs(self, tmp_grades_file, mocked_hook_results):
        """Test that multiple specs works correctly, in the sense that they are
        all registered, but where there are multiple matching issues per repo,
        the grade spec with the lowest priority wins out.
        """
        edit_msg_file = tmp_grades_file.parent / "editmsg.txt"
        args = argparse.Namespace(
            students=list(TEAMS),
            hook_results_file="",  # don't care, read_results_file is mocked
            grades_file=tmp_grades_file,
            assignments="week-1 week-2 week-4 week-6".split(),
            edit_msg_file=str(edit_msg_file),
            teachers=TEACHERS,
            grade_specs=[PASS_GRADESPEC_FORMAT, KOMP_GRADESPEC_FORMAT],
            allow_other_states=False,
        )

        csvgrades.callback(args=args)

        assert _file.read_grades_file(
            tmp_grades_file
        ) == _file.read_grades_file(EXPECTED_GRADES_MULTI_SPEC_FILE)
        assert (
            edit_msg_file.read_text("utf8").strip()
            == EXPECTED_EDIT_MSG_MULTI_SPEC_FILE.read_text("utf8").strip()
        )

    def test_does_not_overwrite_lower_priority_grades(self, tmp_grades_file):
        """Test that e.g. a grade with priority 3 does not overwrite a grade
        with priority 1 that is already in the grades file.
        """
        shutil.copy(str(EXPECTED_GRADES_MULTI_SPEC_FILE), tmp_grades_file)
        slarse, *_ = TEAMS
        hook_result_mapping = {
            _marker.generate_repo_name(str(slarse), "week-4"): [
                create_komp_hookresult(SLARSE_TA)
            ],
            "list-issues": [
                plug.Result(
                    name="list-issues",
                    status=plug.Status.SUCCESS,
                    msg=None,
                    data={"state": plug.IssueState.ALL.value},
                )
            ],
        }
        grades_file_contents = tmp_grades_file.read_text("utf8")
        edit_msg_file = tmp_grades_file.parent / "editmsg.txt"
        args = argparse.Namespace(
            students=[slarse],
            hook_results_file="",  # don't care, read_results_file is mocked
            grades_file=tmp_grades_file,
            assignments=["week-4"],
            edit_msg_file=str(edit_msg_file),
            teachers=list(TEACHERS),
            grade_specs=[PASS_GRADESPEC_FORMAT, KOMP_GRADESPEC_FORMAT],
            allow_other_states=False,
        )

        with mock.patch(
            "repobee_csvgrades._file.read_results_file",
            autospec=True,
            return_value=hook_result_mapping,
        ):
            csvgrades.callback(args=args)

        assert tmp_grades_file.read_text("utf8") == grades_file_contents
        assert not edit_msg_file.exists()

    def test_repos_without_hook_results_are_skipped(
        self, tmp_grades_file, mocked_hook_results
    ):
        """Run with extra repos that have no hook results (week-3)"""
        args = argparse.Namespace(
            students=list(TEAMS),
            hook_results_file="",  # don't care, read_results_file is mocked
            grades_file=tmp_grades_file,
            assignments="week-1 week-2 week-3 week-4 week-6".split(),
            edit_msg_file=str(tmp_grades_file.parent / "editmsg.txt"),
            teachers=list(TEACHERS),
            grade_specs=[PASS_GRADESPEC_FORMAT],
            allow_other_states=False,
        )

        csvgrades.callback(args=args)

        assert _file.read_grades_file(
            tmp_grades_file
        ) == _file.read_grades_file(EXPECTED_GRADES_FILE)

    def test_students_missing_from_grades_file_causes_crash(
        self, tmp_grades_file, mocked_hook_results
    ):
        """Test that if a specified student is missing from the grades
        file, there is a crash.
        """
        missing_team = plug.StudentTeam(members=["randomdude"])
        args = argparse.Namespace(
            students=list(TEAMS) + [missing_team],
            hook_results_file="",  # don't care, read_results_file is mocked
            grades_file=tmp_grades_file,
            assignments="week-1 week-2 week-4 week-6".split(),
            edit_msg_file=str(tmp_grades_file.parent / "editmsg.txt"),
            teachers=list(TEACHERS),
            grade_specs=[PASS_GRADESPEC_FORMAT],
            allow_other_states=False,
        )

        with pytest.raises(_exception.FileError) as exc_info:
            csvgrades.callback(args=args)

        assert "student(s) {} missing from the grades file".format(
            missing_team.members[0]
        ) in str(exc_info.value)

    def test_raises_if_state_is_not_all(
        self, tmp_grades_file, mocked_hook_results
    ):
        """Test that a warning is issued if the plugin is run on ``issues list``
        results where the state is not ``all`` (i.e. ``repobee issues list``
        was not run with the ``--all`` flag). This is important as closed
        issues should still be taken into account.
        """
        args = argparse.Namespace(
            students=list(TEAMS),
            hook_results_file="",  # don't care, read_results_file is mocked
            grades_file=tmp_grades_file,
            assignments="week-1 week-2 week-4 week-6".split(),
            edit_msg_file=str(tmp_grades_file.parent / "editmsg.txt"),
            teachers=list(TEACHERS),
            grade_specs=[PASS_GRADESPEC_FORMAT],
            allow_other_states=False,
        )
        mocked_hook_results["list-issues"] = [
            plug.Result(
                name="list-issues",
                status=plug.Status.SUCCESS,
                msg=None,
                # change the state to OPEN, which will cause any closed
                # grading issues to be missed
                data={"state": plug.IssueState.OPEN.value},
            )
        ]

        with pytest.raises(_exception.FileError) as exc_info:
            csvgrades.callback(args=args)

        assert "`repobee issues list` was not run with the --all flag" in str(
            exc_info.value
        )


def test_register():
    """Just test that there is no crash"""
    plugin.register_plugins([csvgrades])
