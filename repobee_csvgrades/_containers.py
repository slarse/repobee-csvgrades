import collections
import re

import repobee_plug as plug


class GradeSpec(
    collections.namedtuple("GradeSpec", "priority symbol regex".split())
):
    """A GradeSpec is a grade specification triple containing a symbol for
    representing the grade in a grade sheet, a priority for determining which
    grade to pick if multiple are found, and a regex to match against issue
    titles to find grading issues.
    """

    @classmethod
    def from_format(cls, format_str: str):
        r"""Build a GradeSpec tuple from a format string. The format string should
        be on the following form:

        ``<PRIORITY>:<SYMBOL>:<REGEX>``

        The expression must match the regex (\d+):([A-Za-z\d]+):(.+)

        <PRIORITY> is a positive integer value specifying how important the
        grade is. If multiple grading issues are found in the same repository,
        the one with the lowest priority is reported.

        <SYMBOL> is one or more characters specifying how the grade is
        represented in the CSV grade sheet. Only characters matching the regex
        [A-Za-z0-9] are accepted.

        <REGEX> is any valid regex to match against issue titles.

        For example, the format string "P:1:[Pp]ass" will specifies a grade
        spec with symbol P, priority 1 (the lowest possible priority) and will
        match the titles "Pass" and "pass".

        Args:
            format_str: A grade spec format string as defined above.
        Returns:
            A GradeSpec.
        """
        pattern = r"(\d+):([A-Za-z\d]+):(.+)"
        match = re.match(pattern, format_str)
        if not match:
            raise plug.PlugError(
                "invalid format string: {}".format(format_str)
            )
        priority_str, symbol, regex = match.groups()
        priority = int(priority_str)
        return super().__new__(
            cls, symbol=symbol, priority=priority, regex=regex
        )

    def __lt__(self, o):
        return self.priority < o.priority
