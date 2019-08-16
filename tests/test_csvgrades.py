import pathlib
import argparse
import sys
from unittest import mock

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


def test_register():
    """Just test that there is no crash"""
    plugin.register_plugins([csvgrades])


@pytest.fixture
def mocked_hook_results(mocker):
    """Hook results with passes for glassey-glennol in week-1 and week-2, and
    for slarse in week-4 and week-6.
    """
    pass_issue = plug.Issue(
        title="Pass", body="This is a pass", number=3, created_at=datetime(1992, 9, 19)
    )
    other_issue = plug.Issue(
        title="Grading criteria",
        body="This is grading criteria",
        number=1,
        created_at=datetime(2009, 12, 31),
    )
    pass_hookresult = plug.HookResult(
        hook="list-issues",
        status=plug.Status.SUCCESS,
        msg=None,
        data={pass_issue.number: pass_issue.to_dict()},
    )
    other_hookresult = plug.HookResult(
        hook="list-issues",
        status=plug.Status.SUCCESS,
        msg=None,
        data={other_issue.number: other_issue.to_dict()},
    )
    pass_and_other_hookresult = plug.HookResult(
        hook="list-issues",
        status=plug.Status.SUCCESS,
        msg=None,
        data={
            other_issue.number: other_issue.to_dict(),
            pass_issue.number: pass_issue.to_dict(),
        },
    )
    slarse, glassey_glennol = TEAMS
    gen_name = csvgrades.generate_repo_name
    hook_results = {
        gen_name(str(team), repo_name): [result]
        for team, repo_name, result in [
            (slarse, "week-1", other_hookresult),
            (slarse, "week-2", other_hookresult),
            (slarse, "week-4", pass_hookresult),
            (slarse, "week-6", pass_and_other_hookresult),
            (glassey_glennol, "week-1", pass_hookresult),
            (glassey_glennol, "week-2", pass_and_other_hookresult),
            (glassey_glennol, "week-4", other_hookresult),
            (glassey_glennol, "week-6", other_hookresult),
        ]
    }
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
        )

        with mock.patch(
            "repobee_csvgrades.csvgrades.read_results_file",
            return_value=mocked_hook_results,
            autospec=True,
        ):
            csvgrades.callback(args=args, api=None)

        assert csvgrades.read_grades_file(
            tmp_grades_file
        ) == csvgrades.read_grades_file(EXPECTED_GRADES_FILE)
