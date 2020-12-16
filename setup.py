import re
from setuptools import setup, find_packages

with open("README.md", mode="r", encoding="utf-8") as f:
    readme = f.read()

# parse the version instead of importing it to avoid dependency-related crashes
with open("repobee_csvgrades/__version.py", mode="r", encoding="utf-8") as f:
    line = f.readline()
    __version__ = line.split("=")[1].strip(" '\"\n")
    assert re.match(r"^\d+(\.\d+){2}(-(alpha|beta|rc)(\.\d+)?)?$", __version__)

test_requirements = ["pytest", "pytest-cov", "pytest-mock", "tox"]
required = ["repobee>=3.5.0", "dataclasses>='0.7';python_version<'3.7'"]

setup(
    name="repobee-csvgrades",
    version=__version__,
    description=(
        "A plugin for reporting grades into a CSV file based on issue titles"
    ),
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Simon Larsén",
    author_email="slarse@kth.se",
    url="https://github.com/slarse/repobee-csvgrades",
    download_url="https://github.com/"
    "slarse"
    "/repobee-csvgrades"
    "/archive/v{}.tar.gz".format(__version__),
    license="MIT",
    packages=find_packages(exclude=("tests", "docs")),
    tests_require=test_requirements,
    install_requires=required,
    extras_require=dict(TEST=test_requirements),
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.6",
)
