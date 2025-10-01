import os
from smolagents import ToolCallingAgent, LiteLLMModel, tool


class Agent(ToolCallingAgent):
    tool = tool

    def __init__(self, **kwargs):
        _LLM = LiteLLMModel(
            model_id=os.getenv("OPENAI_MODEL_NAME"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        super().__init__(model=_LLM, add_base_tools=False, **kwargs)
