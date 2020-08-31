"""Utility functions for file I/O.

.. module:: _file
    :synopsis: Utility functions for file I/O.

.. moduleauthor:: Simon Larsén
"""
import csv
import sys
import pathlib

import repobee_plug as plug


def read_results_file(results_file):
    if not results_file.is_file():
        raise plug.PlugError(f"no such file: {str(results_file)}")
    return plug.json_to_result_mapping(
        results_file.read_text(encoding=sys.getdefaultencoding())
    )


def read_grades_file(grades_file: pathlib.Path):
    if not grades_file.is_file():
        raise plug.PlugError(f"no such file: {str(grades_file)}")
    with open(
        grades_file, encoding=sys.getdefaultencoding(), mode="r"
    ) as file:
        grades_file_contents = [
            [cell.strip() for cell in row]
            for row in csv.reader(file, delimiter=",")
        ]
        return grades_file_contents[0], grades_file_contents[1:]


def write_edit_msg(new_grades, master_repo_names, edit_msg_file):
    sorted_repo_names = ", ".join(sorted(master_repo_names))

    def format_grade(student, mn, grade):
        return "{} {} {}".format(student, mn, grade)

    teacher_notifications = [
        "@{}\n{}".format(
            teacher, "\n".join([format_grade(*tup) for tup in grades])
        )
        for teacher, grades in new_grades
    ]
    msg = "Report grades for {}\n\n{}".format(
        sorted_repo_names, "\n\n".join(teacher_notifications)
    )
    edit_msg_file.write_text(msg, encoding=sys.getdefaultencoding())


def write_grades_file(grades_file, grades):
    with open(
        str(grades_file), mode="w", encoding=sys.getdefaultencoding()
    ) as dst:
        writer = csv.writer(dst, delimiter=",")
        writer.writerows(grades.csv)
