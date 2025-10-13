import importlib.resources
import pathlib
from typing import Any, Optional
import inspect
from typing import Callable, Union, Literal, get_origin, get_args


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
        - if value is a list, assume all elements inside are of the same type;
        - if the elements are dicts or lists, recursively show their schema,
          otherwise show the type of the first element
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


def tool_annotator(tool: Callable) -> dict:
    """A helper function to convert a function type hints and docstring to a tool definition.
    Args:
        tool (Callable): The function to annotate.
    Returns:
        dict: A dictionary representing the tool definition Conforms to
        OpenAI tool calling interface.
    """
    sig = inspect.signature(tool)
    name = tool.__name__
    doc = tool.__doc__ or ""
    description = doc.strip()

    # Simple docstring parser for parameter descriptions (assumes Google-style)
    param_descriptions = {}
    lines = doc.split("\n")
    in_params = False
    for line in lines:
        line = line.strip()
        if line.lower().startswith("args:") or line.lower().startswith("parameters:"):
            in_params = True
            continue
        if in_params:
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    param, desc = parts
                    param_descriptions[param.strip()] = desc.strip()
            elif not line:
                continue
            else:
                break  # End of params section

    def type_to_json_schema(typ):
        origin = get_origin(typ)
        if origin is None:
            if typ == str:
                return {"type": "string"}
            elif typ == int:
                return {"type": "integer"}
            elif typ == float:
                return {"type": "number"}
            elif typ == bool:
                return {"type": "boolean"}
            else:
                return {"type": "string"}  # default
        elif origin == list:
            args = get_args(typ)
            if args:
                item_schema = type_to_json_schema(args[0])
                return {"type": "array", "items": item_schema}
            else:
                return {"type": "array"}
        elif origin == dict:
            args = get_args(typ)
            if len(args) == 2:
                value_schema = type_to_json_schema(args[1])
                return {"type": "object", "additionalProperties": value_schema}
            else:
                return {"type": "object"}
        elif origin == Union:
            # Handle Optional[T] as Union[T, None] -> schema of T
            args = get_args(typ)
            non_none_args = [arg for arg in args if arg != type(None)]
            if len(non_none_args) == 1:
                return type_to_json_schema(non_none_args[0])
            else:
                # Multiple types, fallback to string
                return {"type": "string"}
        elif origin == Literal:
            args = get_args(typ)
            # Assuming Literal values are strings, as is common; otherwise, enum without type
            if all(isinstance(arg, str) for arg in args):
                return {"type": "string", "enum": list(args)}
            elif all(isinstance(arg, int) for arg in args):
                return {"type": "integer", "enum": list(args)}
            elif all(isinstance(arg, float) for arg in args):
                return {"type": "number", "enum": list(args)}
            elif all(isinstance(arg, bool) for arg in args):
                return {"type": "boolean", "enum": list(args)}
            else:
                # Mixed or other types, fallback to enum list
                return {"enum": list(args)}
        else:
            return {"type": "string"}  # default for other generics

    properties = {}
    required = []
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        schema = {"type": "string"}  # default
        if param.annotation != inspect.Parameter.empty:
            schema = type_to_json_schema(param.annotation)
        desc = param_descriptions.get(param_name, "")
        if desc:
            schema["description"] = desc
        properties[param_name] = schema
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def extract_tool_results(
    messages: list[dict], filter_by_tool: Optional[str] = None
) -> list[dict]:
    """Extract tool results from a list of messages.

    Args:
        messages (list[dict]): List of message dicts.
        filter_by_tool (Optional[str]): If provided, only include results from this tool.

    Returns:
        list[dict]: List of tool result dicts with keys "role", "content", "tool_call_id", "name".
    """
    results = []
    for msg in messages:
        if "tool_call_id" in msg and msg.get("role") == "tool":
            if filter_by_tool is None or msg.get("name") == filter_by_tool:
                results.append(msg)
    return results


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
