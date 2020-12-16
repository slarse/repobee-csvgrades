# repobee-csvgrades

![Build Status](https://github.com/repobee/repobee-csvgrades/workflows/tests/badge.svg)
[![Code Coverage](https://codecov.io/gh/repobee/repobee-csvgrades/branch/master/graph/badge.svg)](https://codecov.io/gh/repobee/repobee-csvgrades)
![Supported Python Versions](https://img.shields.io/badge/python-3.6%2C%203.7%2C%203.8-blue)
![Supported Platforms](https://img.shields.io/badge/platforms-Linux%2C%20macOS-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

> **Important:** repobee-csvgrades v0.2.0 and later require RepoBee 3.

A plugin for reporting grades into a CSV file based on issue titles.
`repobee-csvgrades` adds the `record` category to repobee, along with the `grades` command, which operates on the
JSON file produced by running `repobee list-issues` with the
`--hook-results-file` option. The idea is pretty simple: find issues in student
repositories that match certain user-defined conditions (title + who opened it)
and report the corresponding grades into a (preferably version controlled) CSV
file.

## Example use case
Say that you have three students, `slarse`, `glassey` and `glennol`, three tasks
`task-1`, `task-2` and `task-3`, and that you (and any colleagues) open issues
with titles `Pass` for pass and `Fail` for fail. `repobee-csvgrades` can then
be configured to look for issues with those titles (using a regex), and write
them into a grades sheet that looks something like this:

```
            name,username,task-1,task-2,task-3
    Simon Larsén,  slarse,     P,     P,     F
 Richard Glassey, glassey,     P,     P,     P
    Glenn Olsson, glennol,     P,     P,     P
```

> **GitHub and CSV files:** GitHub
> [renders CSV files really nicely](https://help.github.com/en/articles/rendering-csv-and-tsv-data),
> they are even searchable!

Only grades from issues that were opened by authorized teachers, as specified
by you, are written to the file. Grades are mapped from issue title to a
symbol, so the CSV file becomes more readable (here there's for example `P` for
`Pass`). You also assign grades a priority, so if for example there's both a
fail and a pass issue in a repo, it will pick the one that you've specified is
most important.  Additionally, each time new grades are reported, a summary
message will be produced that looks something like this:

```
Record grades for task-3

@ta_a
slarse task-3 F

@ta_b
glassey task-3 P
```

The `@ta_a` and `@ta_b` are mentions of the teachers/TAs (with usernames `ta_a`
and `ta_b`) that opened the issues. The intention is that this message should be
used as a commit message for the grades file, so that the people who reported
grades get notified of which grades have been written to the grades sheet.

That's just a quick introduction, see [Usage](#usage) for a more detailed
description.

## Install
As of `Repobee 3.0`, installing a plugin is easier than ever. 

First, make sure that you have the latest version of `Repobee` installed,
instructions can be found on the [Repobee website](https://repobee.org/).

To install `repobee-csvgrades`, simply run the command `repobee plugin install`, and this will open up a bullet-list where you can select csvgrades. 

> If `repobee-csvgrades` does not show up when running the `grades record` command. Run `repobee plugin list`, this will present a list with all the availiable plugins. If you cannot find `repobee-csvgrades` in the list, try updating `repobee` using repobee `repobee manage upgrade`.

## Usage
`repobee-csvgrades` is easy to use and highly customizable. First of all, you
need to know how to use a plugin for RepoBee, see the
[RepoBee plugin docs](https://repobee.readthedocs.io/en/stable/plugins.html).
Then, there are a few key parts to familiarize yourself with before using it,
however. The following sections explain the command line options in depth. Also
don't miss the fact that you can configure all options in the
[configuration file](#configuration-file-section).

### The grade specification (`--grade-specs` option)
The grade specification (or _grade spec_) is the most important part of this
plugin. Grade specs tell the `grades record` command which issues to consider as
grading issues, and which grading issues outweigh others if several are found. A
typical grade spec looks like this: `1:P:[Pp]ass`. There are three parts to the
grade spec, delimited by `:`. First is the priority. A lower priority outweighs
a higher priority. Second is the symbol that is written to the CSV grades file.
Third is a regex to match against issue titles. Any issue whos title matches the
regex is considered a grading issues of that spec.

> **Important:** Your grade spec regexes should _not_ overlap (i.e. be able to
> match the same strings). If they do, behavior is undefined.

Grade specs are specified by the `--grade-specs` option. Example:

```
--grade-specs '1:P:[Pp]ass' '2:F:[Ff]ail' '3:C:[Cc]orrection'
```

### The hook results file (`--hook-results-file` option)
`grades record` operates on a file with a JSON database produced by the
`issues list` command (one of RepoBee's core commands). The file is produced by
supplying the `--hook-results-file FILEPATH` option to `issues list`. You
should additionally supply `issues list` with the `--all` flag, to get both open
and closed issues (so as to avoid missing grading issues). If you try to use
`grades record` with a hook results file that's been produced without the
`--all` flag, it will exit with an error. If you really want to run with that
file, you can supply the `--allow-other-states` flag to `grades record`, which
disregards how the hook results were collected.

The hook results file is specified by the `--hook-results-file` option. Example:

```
--hook-results-file ~/some_course/2019/hook_results_jan.json
```

### The grades file (`--grades-file` option)
`grades record` writes grades to a CSV file that we refer to as the _grades
file_. Each row represents one student, except for the first row which is a
header row. The following requirements are placed on the CSV file format:

* Commas must be used as the delimiter
* The first line of the file must be a row of headers
* One of the headers must be `username`, and the column must include the
  usernames of all students to be graded
* There must be one column for each master repo, and the header for that column
  must exactly match the master repo's name

Below is an example grades file that has been partially filled in by the
`grades record` command. As it is a CSV file, it is rendered very nicely on
GitHub (see for example [this test file](/tests/expected_grades.csv)), and it
is strongly recommended that you keep this file in version control.

```
            name,username,task-1,task-2,task-3,task-4,task-5,task-6
    Simon Larsén,  slarse,     P,     P,     F,      ,      ,  
 Richard Glassey, glassey,     P,     P,     P,      ,      ,  
    Glenn Olsson, glennol,     P,     P,     P,      ,      ,  
```

There are a few additional things to keep in mind with the grades file.

* You should not manually edit the file with grade symbols for which there are
  no grade specifications, as this may cause `grades record` to exit because it
  can't find a priority for the grade.
* You can't have a task called `username`.
* You can't have duplicate column headers.
* You **can** have any additional columns that you want. `grades record` will
  only look at the `username` column, and the columns corresponding to the
  master repo names that you specify when calling the command. Additional
  columns will simply not be inspected.
* `grades record` formats the diff file such that every cell of the same column
  has the same width, which makes diffs easy to inspect.
  - Because of this formatting, it is recommended to keep grade spec symbols
    shorter than the master repo names, to avoid resizing of columns when grades
    are entered.

The grades file is specified by the `--grades-file` option. Example:

```
--grades-file ~/some_course/2019/grades.csv
```

### The edit message file (`--edit-msg-file` option)
Each time you run `grades record`, a file is produced specifying what new grades
were recorded, and tags the teachers who opened the grading issues. The
intention is that this edit message should be used as a Git commit message. For
example, if `slarse` has teacher `ta_a`, and `glassey` has teacher `ta_b`, and
they both got new grades for `task-3`, the edit message might look like ths:

```
Record grades for task-3

@ta_a
slarse task-3 F

@ta_b
glassey task-3 P
```

The reason this edit message file exists is that some of our TAs felt a bit
nervous about not knowing when their reported grades were collected. If this
edit message is posted as the commit message, every teacher/TA whos grades have
been collected will be notified, and the extra thorough ones can even inspect
the diff to make sure everything is OK.

The destination for the edit message file is specified by the `--edit-msg-file`
option. Example:

```
--edit-msg-file edit_msg.txt
```

### Authorized teachers (`--teachers` option)
The `grades record` command requires you to specify a set of teachers that are
authorized to open grading issues. This is to avoid having students trick the
system. If an grading issue by an unauthorized user is found, a warning is
emitted. This is both to alert the user about potential attempts at foul play,
but also to help identify teachers that are actually authorized, but have not
been included in the list.

Teachers are specified with the `--teachers` option. Example:

```
--teachers ta_a ta_b
```

## Configuration file section
`repobee-csvgrades` can fetch information from the
[RepoBee configuration file](https://repobee.readthedocs.io/en/stable/getting_started.html#editing-the-configuration-file-the-wizard-and-show-actions),
under the `csvgrades` section. All of the command line options can be
configured. Use the `config wizard` command to configure `csvgrades`.

> **Important:** The plugin must be active when running `config wizard`, or
> otherwise it will not be configurable. Here, we activate it with `-p
> csvgrades`.

```
$ repobee -p csvgrades config wizard
Editing config file at /home/slarse/.config/repobee/config.ini
Select a section to configure:
 repobee
●csvgrades # make sure to select the csvgrades section to configure
```

Note that some of the configurable options are lists, such as the `teachers`
and `grade-specs` options. Simply separate each item in the list with a space,
like you would on the commmand line. If an item contains a space (such as a
regex in a grade spec), the whole item must be surrounded with single quotes.

# License
`repobee-csvgrades` is released under the MIT license. See [LICENSE](LICENSE)
for details.
