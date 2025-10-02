import os
from litellm import supports_reasoning
from smolagents import ToolCallingAgent, LiteLLMModel, tool


class Agent(ToolCallingAgent):
    """The base agent used by this application. All other agents inherit from this."""

    # The function decorator to register tools
    tool = tool

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
