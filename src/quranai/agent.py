import os
from typing import Any, Callable, Iterable, Optional
from inspect import Signature, Parameter

from litellm import supports_reasoning  # pyright: ignore[reportPrivateImportUsage]
from litellm import LiteLLM
from smolagents import LiteLLMModel, ToolCallingAgent, tool

from quranai.llm import LLM
from quranai.utils import tool_annotator


# deprecated
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
        agents: Iterable["CustomBaseAgent"] = (),
        instructions: Optional[str] = None,
        max_turns: int = 5,
        name: Optional[str] = None,
        **kwargs,
    ):
        self.instructions = instructions or "You are a helpful assistant."
        self.max_turns = max_turns
        self.messages: list[dict] = []
        self.tool_defs: dict[str, dict[str, Callable]] = {}
        self.agents: list[CustomBaseAgent] = list(agents)
        self.model = model
        self.name = name
        self._setup(model=model, tools=tools, agents=agents, **kwargs)
        self.reset()

    def _setup(
        self,
        model: LLM,
        tools: Iterable[Callable],
        agents: Iterable["CustomBaseAgent"],
        **kwargs,
    ):
        # See: https://docs.litellm.ai/docs/reasoning_content
        # _llm_kwargs = (
        #     {"reasoning_effort": "low"} if supports_reasoning(_model_name) else {}
        # )
        self.add_tools(*tools)
        self.add_agents(*agents)

    @property
    def state(self) -> dict[str, Any]:
        return {
            "messages": self.messages.copy(),
            "agent_states": (agent.state for agent in self.agents),
        }

    @state.setter
    def state(self, state: dict[str, Any]):
        self.messages = state.get("messages", []).copy()
        agent_states = state.get("agent_states", [])
        for agent, agent_state in zip(self.agents, agent_states):
            agent.state = agent_state

    def add_tools(self, *f: Callable[..., Any]):
        self.tool_defs.update(self.model.prepare_tools(f))

    def add_agents(self, *agents: "CustomBaseAgent"):
        self.agents.extend(agents)
        for agent in agents:
            self.add_tools(agent.as_tool())

    def reset(self):
        del self.messages[:]
        for agent in self.agents:
            agent.reset()

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

    def __call__(self, task: str, state: dict) -> dict:
        """A pure function version of run.

        Args:
            task (str): The task to run.

        Returns:
            dict: The conversation state after running the task.
        """
        _temp = self.state
        try:
            self.state = state
            self.run(task)
        finally:
            state = self.state
            self.state = _temp
        return state

    def as_tool(
        self,
        description: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Callable[[str], str]:
        """Return a callable that can be used as a tool, wrapping the Agent.__call__ method.

        The returned callable has its annotations, __doc__ and __name__ set so that
        inspect.signature and tool_annotator can see parameter types and the
        description.

        Args:
            description (Optional[str]): Optional human-readable description for the tool.
            name (Optional[str]): Optional function name to expose for the tool.

        Returns:
            Callable[[str], str]: A callable that accepts a task string and returns a string.
        """

        def tool_fn(task: str) -> str:
            return self.run(task)

        # Ensure annotations are present so inspect.signature(tool_fn) reports types.
        tool_fn.__annotations__ = {"task": str, "return": str}

        # Also set an explicit __signature__ to be robust for tools that inspect signatures.
        tool_fn.__signature__ = Signature(
            parameters=[
                Parameter("task", Parameter.POSITIONAL_OR_KEYWORD, annotation=str)
            ],
            return_annotation=str,
        )

        if description is None:
            description = (
                "A helpful assistant that can independently answer specialist questions "
                "based on its role."
            )
        description = (
            description
            + "\n\nArgs:\n    task (str): The task to run.\n\nReturns:\n    str: The result of the task."
        )
        tool_fn.__doc__ = description

        if not isinstance(name, str):
            assert (
                isinstance(self.name, str) and self.name.isidentifier()
            ), f"Invalid tool name: {self.name}"
        else:
            assert name.isidentifier(), f"Invalid tool name: {name}"
        tool_fn.__name__ = name or self.name
        tool_fn.__qualname__ = name or self.name

        return tool_fn
