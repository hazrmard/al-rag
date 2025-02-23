from typing import Self
from pydantic import BaseModel, Field
from llm import LLM


class _CoTResponseFormat(BaseModel):
    observation: str = Field(
        description="Internal thoughts about the task to plan for the final answer.",
    )
    action: str = Field(
        description="Next steps that need to be taken to provide the final answer.",
    )
    final_answer: str = Field(description="The final answer to be given to the user.")

    @classmethod
    def response(cls, obj: Self):
        return obj.final_answer


class CoTAgent(LLM):
    response_format = _CoTResponseFormat

    def __init__(self, *, tools: list[callable] = ()) -> None:
        super().__init__(tools=tools)
        self._messages = []  # passed to LLM
        self.messages = []  # displayed to user

    def chat(self, message: str | dict) -> dict:
        tool_resp = True
        final_answer = ""
        self._messages.append(dict(role="user", content=message))
        while not final_answer:
            resp = self.complete(self._messages, response_format=self.response_format)
            llm_resp = self.llm_responses(resp=resp)
            llm_resp_obj = self.response_format.model_validate_json(
                llm_resp[0]["content"]
            )
            final_answer = self.response_format.response(llm_resp_obj)
            tool_resp = self.tool_responses(resp=resp)
            self._messages.extend(llm_resp)
            self._messages.extend(tool_resp)
        self.messages.append(dict(role="assistant", content=final_answer))
        return self.messages[-1]
