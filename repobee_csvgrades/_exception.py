"""Exception classes."""
import repobee_plug as plug


class FileError(plug.PlugError):
    """Raise when there is something wrong with one of the files."""


class GradingError(plug.PlugError):
    """Raise when attempting to do something inappropriate with grading"""
