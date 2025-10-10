import os
from typing import Any, Callable, Iterable, Optional

from litellm import supports_reasoning  # pyright: ignore[reportPrivateImportUsage]
from litellm import LiteLLM
from smolagents import LiteLLMModel, ToolCallingAgent, tool

from quranai.llm import LLM
from quranai.utils import tool_annotator


class Agent(ToolCallingAgent):
    """The base agent used by this application. All other agents inherit from this."""

    # The function decorator to register tools
    tool = lambda fn: dict(type="function", function=tool(fn))

    def __init__(self, **kwargs):
        _model_name = os.getenv("OPENAI_MODEL_NAME")
        assert _model_name, "Please set the OPENAI_MODEL_NAME environment variable."
        # See: https://docs.litellm.ai/docs/reasoning_content
        _llm_kwargs = (
            {"reasoning_effort": "low"} if supports_reasoning(_model_name) else {}
        )
        _LLM = LiteLLMModel(
            model_id=_model_name, api_key=os.getenv("OPENAI_API_KEY"), **_llm_kwargs
        )
        super().__init__(model=_LLM, add_base_tools=False, max_steps=5, **kwargs)


class CustomBaseAgent:
    """A custom base agent to be used by this application. All other agents inherit from this."""

    # The function decorator to register tools
    tool = tool_annotator

    def __init__(
        self,
        model: LLM,
        tools: Iterable[Callable] = (),
        instructions: Optional[str] = None,
        max_turns: int = 5,
        **kwargs,
    ):
        self.instructions = instructions or "You are a helpful assistant."
        self.max_turns = max_turns
        self.messages: list[dict] = []
        self.tool_defs: dict[str, dict[str, Callable]] = {}
        self.model = model
        self._setup(model=model, tools=tools, **kwargs)
        self.reset()

    def _setup(self, model: LLM, tools: Iterable[Callable], **kwargs):
        # See: https://docs.litellm.ai/docs/reasoning_content
        # _llm_kwargs = (
        #     {"reasoning_effort": "low"} if supports_reasoning(_model_name) else {}
        # )
        self.add_tools(*tools)

    def add_tools(self, *f: Callable[..., Any]):
        self.tool_defs.update(self.model.prepare_tools(f))

    def reset(self):
        self.messages = []

    def run(self, task: str):
        """Run the agent on a given task.
        The agent loops until there are no more tool calls to make.
        The state is maintained in self.messages.

        Args:
            task (str): The task to run.

        Returns:
            str: The result of the task.
        """
        turn = 0
        while turn < self.max_turns:
            turn += 1
            is_final_turn = turn == self.max_turns
            outbound_messages = (
                [{"role": "system", "content": self.instructions}]
                + self.messages
                + [{"role": "user", "content": task}]
            )
            new_messages = self.model.run(
                messages=outbound_messages,
                tool_defs=None if is_final_turn else self.tool_defs,
            )
            self.messages.extend(new_messages)
            if all("tool_call_id" not in m for m in new_messages):
                break
        return self.messages[-1]["content"]
