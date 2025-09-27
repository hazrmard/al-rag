from typing import Self, Iterable
from pydantic import BaseModel, Field
from llm import LLM


class _CoTResponseFormat(BaseModel):
    observations: list[str] = Field(
        description="Internal thoughts about the task to plan for the final answer.",
    )
    actions: list[str] = Field(
        description="Next steps that need to be taken to provide the final answer.",
    )
    final_answer: str = Field(
        description="The final answer to be given to the user. This can be empty if a tool is being called."
    )

    @classmethod
    def response(cls, obj: Self):
        return obj.final_answer


class CoTAgent(LLM):
    response_format = _CoTResponseFormat
    system_prompt = """\
        You are a helpful assistant who responds in a factual and polite manner. 
        You analyze the user's questions and formulate a response plan before 
        giving the final answer. Think step by step.\
    """

    def __init__(
        self, *, tools: list[callable] = (), system_prompt: str = None
    ) -> None:
        super().__init__(tools=tools)
        self.system_prompt = system_prompt or self.system_prompt
        self._messages = [
            dict(role="system", content=self.system_prompt)
        ]  # passed to LLM

    def chat(self, message: str | dict) -> dict:
        tool_resp = True
        final_answer = ""
        self._messages.append(dict(role="user", content=message))
        while not final_answer:
            resp = super().complete(
                self._messages, response_format=self.response_format
            )
            llm_resp = self.llm_responses(resp=resp)
            llm_resp_obj = self.response_format.model_validate_json(
                llm_resp[0]["content"]
            )
            final_answer = self.response_format.response(llm_resp_obj)
            tool_resp = self.tool_responses(resp=resp)
            self._messages.extend(llm_resp)
            self._messages.extend(tool_resp)
        return dict(role="assistant", content=final_answer)

    @property
    def messages(self) -> Iterable[dict]:
        for m in self._messages:
            if m["role"] == "user":
                yield m
            elif m["role"] == "assistant":
                try:
                    msg = self.response_format.model_validate_json(m)
                    yield dict(
                        role="assistant", content=self.response_format.response(msg)
                    )
                except Exception as exc:
                    yield msg
