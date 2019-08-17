import pathlib
import argparse
import sys

import pytest
from _repobee import plugin
import repobee_plug as plug
import shutil
from datetime import datetime

from repobee_csvgrades import csvgrades

TEAMS = tuple(
    [plug.Team(members=members) for members in (["slarse"], ["glassey", "glennol"])]
)
DIR = pathlib.Path(__file__).parent
GRADES_FILE = DIR / "grades.csv"
EXPECTED_GRADES_FILE = DIR / "expected_grades.csv"
EXPECTED_EDIT_MSG_FILE = DIR / "expected_edit_msg.txt"


def test_register():
    """Just test that there is no crash"""
    plugin.register_plugins([csvgrades])


@pytest.fixture
def mocked_hook_results(mocker):
    """Hook results with passes for glassey-glennol in week-1 and week-2, and
    for slarse in week-4 and week-6.
    """

    def create_pass_hookresult(author):
        pass_issue = plug.Issue(
            title="Pass",
            body="This is a pass",
            number=3,
            created_at=datetime(1992, 9, 19),
            author=author,
        )
        return plug.HookResult(
            hook="list-issues",
            status=plug.Status.SUCCESS,
            msg=None,
            data={pass_issue.number: pass_issue.to_dict()},
        )

    def create_other_hookresult(author):
        other_issue = plug.Issue(
            title="Grading criteria",
            body="This is grading criteria",
            number=1,
            created_at=datetime(2009, 12, 31),
            author=author,
        )
        return plug.HookResult(
            hook="list-issues",
            status=plug.Status.SUCCESS,
            msg=None,
            data={other_issue.number: other_issue.to_dict()},
        )

    def create_other_and_pass_hookresult(author):
        other = create_other_hookresult(author)
        pass_ = create_pass_hookresult(author)
        return plug.HookResult(
            hook="list-issues",
            status=plug.Status.SUCCESS,
            msg=None,
            data={**other.data, **pass_.data},
        )

    slarse, glassey_glennol = TEAMS
    slarse_ta = "ta_a"
    glassey_glennol_ta = "ta_b"
    gen_name = csvgrades.generate_repo_name
    hook_results = {
        gen_name(str(team), repo_name): [result]
        for team, repo_name, result in [
            (slarse, "week-1", create_other_hookresult(slarse_ta)),
            (slarse, "week-2", create_other_hookresult(slarse_ta)),
            (slarse, "week-4", create_pass_hookresult(slarse_ta)),
            (slarse, "week-6", create_other_and_pass_hookresult(slarse_ta)),
            (glassey_glennol, "week-1", create_pass_hookresult(glassey_glennol_ta)),
            (
                glassey_glennol,
                "week-2",
                create_other_and_pass_hookresult(glassey_glennol_ta),
            ),
            (glassey_glennol, "week-4", create_other_hookresult(glassey_glennol_ta)),
            (glassey_glennol, "week-6", create_other_hookresult(glassey_glennol_ta)),
        ]
    }
    mocker.patch(
        "repobee_csvgrades.csvgrades.read_results_file",
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
    def test_correctly_marks_passes(self, tmp_grades_file, mocked_hook_results, mocker):
        args = argparse.Namespace(
            students=list(TEAMS),
            hook_results_file="",  # don't care, read_results_file is mocked
            grades_file=str(tmp_grades_file),
            master_repo_names="week-1 week-2 week-4 week-6".split(),
            edit_msg_file=str(tmp_grades_file.parent / "editmsg.txt"),
        )

        csvgrades.callback(args=args, api=None)

        assert csvgrades.read_grades_file(
            tmp_grades_file
        ) == csvgrades.read_grades_file(EXPECTED_GRADES_FILE)

    def test_writes_edit_msg(self, tmp_grades_file, mocked_hook_results, mocker):
        edit_msg_file = tmp_grades_file.parent / "editmsg.txt"
        args = argparse.Namespace(
            students=list(TEAMS),
            hook_results_file="",  # don't care, read_results_file is mocked
            grades_file=str(tmp_grades_file),
            master_repo_names="week-1 week-2 week-4 week-6".split(),
            edit_msg_file=str(edit_msg_file),
        )

        csvgrades.callback(args=args, api=None)

        assert edit_msg_file.read_text(
            sys.getdefaultencoding()
        ).strip() == EXPECTED_EDIT_MSG_FILE.read_text(sys.getdefaultencoding()).strip()
