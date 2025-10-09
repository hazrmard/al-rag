import os
import sys
from typing import Callable, Optional, Iterable, Any
import json
from dotenv import load_dotenv
import litellm
from litellm import completion
import litellm.types.utils
from litellm.utils import function_to_dict as f2d
import litellm.types
from quranai.utils import tool_annotator


class LLM:
    """The base LLM class. Can use any number of public libraries to call LLM APIs.

    Example usage:

        llm = LLM(tools=(my_tool_function,))
        messages = [{"role": "user", "content": "What is the capital of France?"}]
        response = llm.run(messages)
        print(response[-1])

    """

    def __init__(self, *, tools: Iterable[Callable] = (), model_name: str = "") -> None:
        self.tools = {}
        self.llm_kwargs: dict[str, Any] = {}
        self.tools.update(self.prepare_tools(tools))
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

    def add_tools(self, *f: Callable[..., Any]):
        self.tools.update(self.prepare_tools(f))

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
        self, messages: list[dict], **kwargs
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
            tools=[f["defn"] for f in self.tools.values()] if self.tools else None,
        )
        llm_kwargs.update(self.llm_kwargs)  # override with any kwargs provided
        llm_kwargs.update(kwargs)  # override with any kwargs provided
        resp = self.completion(**llm_kwargs)  # pyright: ignore[reportArgumentType]
        assert isinstance(resp, litellm.types.utils.ModelResponse)
        return resp

    def run(
        self, messages: list[dict], system_prompt: Optional[str] = None
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
        response = self.complete(messages)
        return self.llm_responses(response) + self.tool_responses(response)

    def run_once(self, task: str, system_prompt: Optional[str] = None) -> str:
        messages = [{"role": "user", "content": task}]
        return self.run(messages, system_prompt=system_prompt)[-1]["content"]

    def tool_responses(
        self,
        resp: litellm.types.utils.ModelResponse,
        *,
        tools: Optional[Iterable[Callable[..., Any]]] = None,
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
        if tools is not None:
            tool_defs = self.prepare_tools(tools)
        else:
            tool_defs = self.tools
        return tool_responses(resp, tools=tool_defs, **kwargs)

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
    tool_defs: dict[str, dict],
    **kwargs,
) -> list[dict]:
    """Execute tools called by an LLM response and return the results as dicts.

    Parameters
    ----------
    response : litellm.types.utils.ModelResponse
        The result of the LLM call.
    tool_defs : dict[str, dict]
        A mapping of tool names to their definitions and functions.
        For example: dict(tool_name={"defn": tool_def, "func": tool_function}, ...)
    **kwargs : dict
        Additional keyword arguments to pass to tool functions.

    Returns
    -------
    list[dict]
        Results of tool calls
    """
    # TODO: concurrent / async calls
    resp = response.choices[0]
    msgs = []
    if resp.message.tool_calls:
        for call in resp.message.tool_calls:
            tid = call.id
            name = call.function.name
            func = tool_defs[name]["func"]
            args = json.loads(call.function.arguments)
            print("Calling tool %s with args: %s" % (name, args), file=sys.stderr)
            try:
                # try running where function accepts local_vars (code_sandbox)
                args.update(kwargs)  # override app provided args on top of llm args
                result = func(**args)
            except Exception as exc:
                result = f"Error: {exc}"
                print("Tool %s raised an exception: %s" % (name, exc), file=sys.stderr)
            msg = {"tool_call_id": tid, "role": "tool", "name": name, "content": result}
            msgs.append(msg)
    return msgs
