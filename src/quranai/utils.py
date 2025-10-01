import importlib.resources
import pathlib
from typing import Any


def list_data_files():
    """List all files in the quranai/data directory."""
    try:
        files = []
        for item in importlib.resources.files("quranai.data").iterdir():
            if item.is_file():
                files.append(item.name)
        return files
    except FileNotFoundError:
        return []


def get_data_file_path(filename) -> pathlib.Path:
    """Get the Traversable path to a data file."""
    return importlib.resources.files("quranai.data") / filename


def read_data_file(filename) -> str:
    """Read the content of a data file as text."""
    return importlib.resources.read_text("quranai.data", filename)


def schema(d: dict | list) -> str:
    """Pretty-formatted schema of a json object (dict or list).

    For dicts, for each key, value:
        - if value is a list, assume all elements inside are of the same type; if the elements are dicts or lists, recursively show their schema, otherwise show the type of the first element,
        - if value is a dict, recursively call schema on it,
        - otherwise, show the type of the value.

    For lists, assume all elements are of the same type and show accordingly.
    """
    if not isinstance(d, (dict, list)):
        return f"{type(d).__name__}"

    if isinstance(d, list):
        if not d:
            return "list of unknown"
        first = d[0]
        if isinstance(first, (dict, list)):
            nested_schema = schema(first)
            indented_schema = "\n".join(
                "  " + line for line in nested_schema.split("\n")
            )
            return f"list of {type(first).__name__}:\n{indented_schema}"
        else:
            return f"list of {type(first).__name__}"

    schema_lines = []
    for key, value in d.items():
        if isinstance(value, list):
            if value:
                first = value[0]
                if isinstance(first, (dict, list)):
                    nested_schema = schema(first)
                    indented_schema = "\n".join(
                        "  " + line for line in nested_schema.split("\n")
                    )
                    schema_lines.append(
                        f"{key}: list of {type(first).__name__}:\n{indented_schema}"
                    )
                else:
                    element_type = type(first).__name__
                    schema_lines.append(f"{key}: list of {element_type}")
            else:
                schema_lines.append(f"{key}: list of unknown")
        elif isinstance(value, dict):
            nested_schema = schema(value)
            indented_schema = "\n".join(
                "  " + line for line in nested_schema.split("\n")
            )
            schema_lines.append(f"{key}:\n{indented_schema}")
        else:
            schema_lines.append(f"{key}: {type(value).__name__}")

    return "\n".join(schema_lines)


class SingletonMeta(type):
    """Metaclass for creating singleton classes.

    Ensures that only one instance of a class exists throughout the application.
    Useful for classes with expensive initialization, like loading large indexes.

    Example usage:
        class TopicIndex(metaclass=SingletonMeta):
            def __init__(self):
                # Expensive initialization here
                pass
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
