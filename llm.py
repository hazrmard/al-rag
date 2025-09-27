import os
import json
from dotenv import load_dotenv
import litellm
from litellm import completion
import litellm.types.utils
from litellm.utils import function_to_dict as f2d

# from langchain_core.utils.function_calling import convert_to_openai_function
import litellm.types

load_dotenv(override=True)

assert "OPENAI_API_KEY" in os.environ


class LLM:
    """The base LLM class. Can use any number of public libraries to call LLM APIs."""

    model_name = "gpt-4o"

    def __init__(self, *, tools: list[callable] = ()) -> None:
        self.tools = {}
        for f in tools:
            self._add_tool(f)

    def _add_tool(self, f: callable):
        defn = convert_to_openai_function(f)  # more verbose
        # defn = f2d(f)
        self.tools[defn["name"]] = dict(
            defn=dict(type="function", function=defn), func=f
        )

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
        resp = completion(
            model=f"openai/{self.model_name}",
            messages=list(messages),
            temperature=0.0,
            tools=[f["defn"] for f in self.tools.values()] if self.tools else None,
            **kwargs,
        )
        return resp

    def tool_responses(
        self, resp: litellm.types.utils.ModelResponse, local_vars: dict = {}, **kwargs
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
        return tool_responses(resp, llm=self, local_vars=local_vars, **kwargs)

    def llm_responses(self, resp: litellm.types.utils.ModelResponse) -> list[dict]:
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
    llm: LLM,
    local_vars: dict = {},
    **kwargs,
) -> list[dict]:
    """Execute tools called by an LLM response and return the results as dicts.

    Parameters
    ----------
    response : litellm.types.utils.ModelResponse
        The result of the LLM call.
    llm : LLM
        The LLM instance containing references to tools.

    Returns
    -------
    list[dict]
        Results of tool calls
    """
    resp = response.choices[0]
    msgs = []
    if resp.message.tool_calls:
        for call in resp.message.tool_calls:
            tid = call.id
            name = call.function.name
            func = llm.tools[name]["func"]
            args = json.loads(call.function.arguments)
            print("Calling tool %s" % name)
            try:
                # try running where function accepts local_vars (code_sandbox)
                argsc = args.copy()
                if "local_vars" in argsc:  # ensure llm does not override local vars
                    del argsc["local_vars"]
                argsc.update(kwargs)  # override app provided args on top of llm args
                result = func(local_vars=local_vars, **argsc)
            except TypeError:
                print("Tool %s does not accept local_vars, trying without." % name)
                # otherwise run function without local_vars
                args.update(kwargs)  # override app provided args on top of llm args
                result = func(**args)
            msg = {"tool_call_id": tid, "role": "tool", "name": name, "content": result}
            msgs.append(msg)
    return msgs
