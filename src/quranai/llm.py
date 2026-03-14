# NOTE: depracated
import concurrent.futures
import json
import os
import sys
from typing import Any, Callable, Dict, Iterable, List, Optional

import litellm
import litellm.types
import litellm.types.utils
from dotenv import load_dotenv
from litellm import completion
from litellm.utils import function_to_dict as f2d

from quranai.utils import tool_annotator


class LLM:
    """The base LLM class. Can use any number of public libraries to call LLM APIs.
    This is stateless, except for llm configuration.

    Example usage:

        llm = LLM()
        tool_defs = LLM.prepare_tools([my_tool_function])
        messages = [{"role": "user", "content": "What is the capital of France?"}]
        response = llm.run(messages, tool_defs=tool_defs)
        print(response[-1])

    """

    def __init__(self, *, model_name: str = "") -> None:
        self.llm_kwargs: dict[str, Any] = {}
        self._setup(model_name=model_name)

    @classmethod
    def prepare_tools(
        cls, f: Iterable[Callable], *, tool_annotator: Callable = tool_annotator
    ) -> dict:
        tools = {}
        for fn in f:
            defn = tool_annotator(fn)
            tools[defn["function"]["name"]] = dict(defn=defn, func=fn)
        return tools

    def _setup(self, model_name: str = "", **kwargs) -> None:
        """Used for dependency injection during tests."""
        self.model_name: str = model_name or f"openai/{os.getenv('OPENAI_MODEL_NAME')}"
        self.api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.llm_kwargs = dict(
            model=self.model_name,
            api_key=self.api_key,
            stream=False,
        )
        self.llm_kwargs.update(kwargs)  # override with any kwargs provided
        self.completion = completion

    def complete(
        self, messages: list[dict], tool_defs: Optional[dict] = None, **kwargs
    ) -> litellm.types.utils.ModelResponse:
        """Generates a response message after a list of messages.

        Args:
            messages (list[dict]): List of dicts representing messages:

                role: user, content: MESSAGE
                role: assistant, content: MESSAGE
                ...

        Returns:
            ModelResponse: A response object like the one returned by calling OpenAI models.
        """
        llm_kwargs: dict[str, Any] = dict(
            messages=list(messages),
            tools=([f["defn"] for f in tool_defs.values()] if tool_defs else None),
        )
        llm_kwargs.update(self.llm_kwargs)  # override with any kwargs provided
        llm_kwargs.update(kwargs)  # override with any kwargs provided
        resp = self.completion(**llm_kwargs)  # pyright: ignore[reportArgumentType]
        assert isinstance(resp, litellm.types.utils.ModelResponse)
        return resp

    def run(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        tool_defs: Optional[dict] = None,
    ) -> list[dict]:
        """Runs the LLM on the given messages, executing tool calls if any.

        Args:
            messages (list[dict]): The messages to send to the LLM.
            system_prompt (Optional[str], optional): An optional system prompt to include. Defaults to None.

        Returns:
            list[dict]: The LLM's responses in the standard format.
        """
        if system_prompt:
            if messages[0]["role"] != "system":
                messages = [{"role": "system", "content": system_prompt}] + messages
            else:
                messages = [{"role": "system", "content": system_prompt}] + messages[1:]
        response = self.complete(messages, tool_defs=tool_defs)
        return self.llm_responses(response) + self.tool_responses(
            response, tool_defs=tool_defs
        )

    def run_once(self, task: str, system_prompt: Optional[str] = None) -> str:
        messages = [{"role": "user", "content": task}]
        return self.run(messages, system_prompt=system_prompt)[-1]["content"]

    def tool_responses(
        self,
        resp: litellm.types.utils.ModelResponse,
        *,
        tool_defs: Optional[dict] = None,
        **kwargs,
    ) -> list[dict]:
        """Execute tools called by the LLM, and return the result as message objects.
        Any kwargs passed are used to override args provided to function.

        Parameters
        ----------
        resp : litellm.types.utils.ModelResponse
            The result of the LLM call function.

        Returns
        -------
        list[dict]
            A list of dicts with keys "role", "content", "tool_call_id", "name"
        """
        if tool_defs is None:
            return []
        return tool_responses(resp, tool_defs=tool_defs, **kwargs)

    @classmethod
    def llm_responses(cls, resp: litellm.types.utils.ModelResponse) -> list[dict]:
        """Extract the LLM message from the response of the llm call.

        Parameters
        ----------
        resp : litellm.types.utils.ModelResponse
            The result of the LLM call function.

        Returns
        -------
        list[dict]
            A list of dicts with keys "role", "content".
        """
        return [resp.choices[0].message.model_dump()]


def tool_responses(
    response: litellm.types.utils.ModelResponse,
    tool_defs: Dict[str, Dict],
    **kwargs,
) -> List[Dict]:
    """Execute tools called by an LLM response and return the results as dicts.

    Parameters
    ----------
    response : litellm.types.utils.ModelResponse
        The result of the LLM call.
    tool_defs : Dict[str, Dict]
        A mapping of tool names to their definitions and functions.
        For example: dict(tool_name={"defn": tool_def, "func": tool_function}, ...)
    **kwargs : Dict
        Additional keyword arguments to pass to tool functions.

    Returns
    -------
    List[Dict]
        Results of tool calls
    """
    resp = response.choices[0]
    if not resp.message.tool_calls:
        return []

    # Use ThreadPoolExecutor for concurrent execution of I/O-bound tool calls
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for call in resp.message.tool_calls:
            tid = call.id
            name = call.function.name
            func = tool_defs[name]["func"]
            args = json.loads(call.function.arguments)
            args.update(kwargs)  # override app provided args on top of llm args
            print("Calling tool %s with args: %s" % (name, args), file=sys.stderr)
            future = executor.submit(func, **args)
            futures.append((future, tid, name))

        msgs = []
        for future, tid, name in futures:
            try:
                result = str(future.result())
            except Exception as exc:
                result = f"Error: {exc}"
                print("Tool %s raised an exception: %s" % (name, exc), file=sys.stderr)
            msg = {"tool_call_id": tid, "role": "tool", "name": name, "content": result}
            msgs.append(msg)
    return msgs
