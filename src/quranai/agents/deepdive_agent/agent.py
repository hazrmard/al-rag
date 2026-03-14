"""
DeepDive Agent:

This is a sequential agent comprising of:

1. A looping agent for planning (with a max number of iterations):
    a. A planner agent that uses metadata tools (topics, chapter intros) on the corpus to create a plan for answering the query.
    b. A critique agent that reviews the plan. If sufficient, it exits the loop with the plan in the agent state. If not, it provides feedback.
2. A looping agent for research synthesis (with a max number of iterations):
    a. A synthesizer agent that combines the fetched evidence into a final answer with citations. The answer is saved in the agent state.
    c. A critique agent that reviews the answer. If sufficient, it exits the loop with the synthesized answer in the state. If not, it provides feedback.
"""

from typing import AsyncGenerator
import logging

from google.adk.agents.llm_agent import Agent
from google.adk.agents import BaseAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.exit_loop_tool import exit_loop
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents import BaseAgent, InvocationContext, SequentialAgent, LoopAgent
from google.genai import types
from google.adk.events import Event, EventActions

from quranai.quran import tools

MAX_ITERATIONS = 2
LOOP_COMPLETION_PHRASE = "EXIT_LOOP"
MODEL_NAME = "gemini-3-flash-preview"


# --- Planning agent ---
def update_initial_state(key: str):
    def update_initial_state(callback_context: CallbackContext):
        """Ensure 'initial_topic' is set in state before pipeline starts."""
        if callback_context.user_content and callback_context.user_content.parts:
            callback_context.state[key] = callback_context.user_content.parts[0].text
            logging.info(
                f"In {callback_context.agent_name} updated initial state with {key}: {callback_context.state[key]}"
            )
        else:
            logging.warning(
                f"In {callback_context.agent_name} could not update initial state with {key} because user_content is missing or malformed."
            )

    return update_initial_state


def return_final_response(key: str):
    def _return_final_response(callback_context: CallbackContext):
        # status = callback_context.session.state.get("plan_feedback", "").strip()
        # should_stop = status == LOOP_COMPLETION_PHRASE
        # if should_stop:
        final_answer = callback_context.state[key]
        logging.info(callback_context.state.to_dict())
        logging.info(
            f"In {callback_context.agent_name} returning final answer: {final_answer}"
        )
        return types.Content(parts=[types.Part(text=final_answer)], role="model")

    return _return_final_response


class CheckStatusAndEscalate(BaseAgent):

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        status = ctx.session.state.get("plan_feedback", "").strip()
        should_stop = status == LOOP_COMPLETION_PHRASE
        if should_stop:
            final_answer = ctx.session.state["plan"]
            yield Event(
                author=self.name,
                actions=EventActions(escalate=should_stop, skip_summarization=True),
                # content=types.Content(
                #     parts=[types.Part(text=final_answer)], role="model"
                # ),
            )
        else:
            yield Event(
                author=self.name,
                actions=EventActions(escalate=should_stop, skip_summarization=True),
            )


initial_plan_writer = Agent(
    model=MODEL_NAME,
    name="Initial_Plan_Writer",
    description="Make initial plan for the research topic.",
    include_contents="none",
    instruction=f"""
        Use the provided tools to conduct meta-analysis of sources and formulate a research plan.

        Use the information of the tools, and optionally results from the tools to create 
        a rough research plan outline. Do not attempt to answer the question. Only write 
        a research plan that will be executed later on.

        The research plan should outline the main headers. Inside each header, it should have 
        a brief plan. It should hint towards the tools to use and how to use them.

        Topic:
        ```
        {{query}}
        ```
        Important:
        - Only output the plan. Do not add explanations or any other text.
        """,
    tools=[
        tools.get_chapter_intro,
        tools.get_chapter_intros_by_query,
        tools.get_verses,
        tools.get_verse_footnotes,
        tools.get_verses_for_query,
        tools.get_topics_for_query,
        tools.get_verses_for_topic,
    ],
    output_key="plan",
)

planner_critic_in_loop = Agent(
    model=MODEL_NAME,
    name="Planner_Critic",
    description="Review the plan created by the planner agent.",
    include_contents="none",
    instruction=f"""
        Review the following research plan for the topic.
        If it is sufficient, respond *exactly* and *only* with {LOOP_COMPLETION_PHRASE}
        If not, provide feedback on how to improve it. Use information about available tools 
        to critique how best to use those tools to answer the question.
        Do not attempt to answer the topic.

        Topic:
        ```
        {{query}}
        ```
        Plan:
        ```
        {{plan}}
        ```
        """,
    tools=[
        tools.get_chapter_intro,
        tools.get_chapter_intros_by_query,
        tools.get_verses,
        tools.get_verse_footnotes,
        tools.get_verses_for_query,
        tools.get_topics_for_query,
        tools.get_verses_for_topic,
    ],
    output_key="plan_feedback",
)

planner_in_loop = Agent(
    model=MODEL_NAME,
    name="Plan_Writer",
    description="Iterate on the research plan given the query and feedback.",
    include_contents="none",
    instruction="""
        Use the provided tools to refine the initial research plan for the research topic:
        ```
        {query}
        ```
        Current plan:
        ```
        {plan}
        ```
        Feedback on initial plan (if any):
        ```
        {plan_feedback}
        ```
        IMPORTANT:
        - Do not add explanations in your response.
        - Do not attempt to answer the topic.
        """,
    tools=[
        tools.get_chapter_intro,
        tools.get_chapter_intros_by_query,
        tools.get_verses,
        tools.get_verse_footnotes,
        tools.get_verses_for_query,
        tools.get_topics_for_query,
        tools.get_verses_for_topic,
    ],
    output_key="plan",
)

planner_refinement_loop = LoopAgent(
    name="Planner_Refinement_Loop",
    description="Iteratively refine the research plan until it is sufficient.",
    sub_agents=[
        planner_critic_in_loop,
        CheckStatusAndEscalate(name="CheckStatusAndEscalate"),
        planner_in_loop,
    ],
    max_iterations=MAX_ITERATIONS,
    after_agent_callback=return_final_response("plan"),
)

planner_agent = SequentialAgent(
    name="Planner_Agent",
    description="Agent that plans research steps for answering the query.",
    sub_agents=[
        initial_plan_writer,
        planner_refinement_loop,
    ],
    before_agent_callback=update_initial_state(key="query"),
)

# --- Synthesis agent ---
synthesizer_in_loop = Agent(
    model=MODEL_NAME,
    name="Synthesizer",
    include_contents="none",
    description="Execute the research plan with the help of tools and write a report.",
    instruction="""
    You are a research assistant. Use the topic, research plan, and review (if any) to 
    write or revise the answer.

    IMPORTANT:
    - All factual statements must be cited with the verse or footnote number.
    - Verses are in the format ch:verse. Footnotes are in the format [ref], where
      `ref` is a letter or a number.

    Topic: {query}

    Research Plan:

    {plan}

    Critique / Feedback:

    {answer_feedback?}
    """,
    tools=[
        tools.get_chapter_intro,
        tools.get_chapter_intros_by_query,
        tools.get_verses,
        tools.get_verse_footnotes,
        tools.get_verses_for_query,
        tools.get_topics_for_query,
        tools.get_verses_for_topic,
    ],
    output_key="answer",
)

synthesizer_critic_in_loop = Agent(
    model=MODEL_NAME,
    name="Synthesizer_Critic",
    include_contents="none",
    description="Review the synthesized answer.",
    instruction=f"""
    You are a research reviewer. Review the following research, given the initial query and 
    research plan. Provide feedback in regards to completeness, sources, and quality of 
    the response. You have access to the same tools as the research writer. They can be used to
    suggest refinements.

    The research may only have addressed a portion of the plan. Guide the writer through 
    steps to improve the answer.

    IMPORTANT:
    - If the answer is adequate, respond *exactly* and *only* with {LOOP_COMPLETION_PHRASE}

    Topic: {{query}}

    Research Plan:

    {{plan}}

    Answer:

    {{answer}}
    """,
    tools=[
        tools.get_chapter_intro,
        tools.get_chapter_intros_by_query,
        tools.get_verses,
        tools.get_verse_footnotes,
        tools.get_verses_for_query,
        tools.get_topics_for_query,
        tools.get_verses_for_topic,
    ],
    output_key="answer_feedback",
)

synthesizer_refinement_loop = LoopAgent(
    name="Synthesizer_Refinement_Loop",
    description="Iteratively refine the synthesized answer until it is sufficient.",
    sub_agents=[
        synthesizer_in_loop,
        synthesizer_critic_in_loop,
        CheckStatusAndEscalate(name="CheckStatusAndEscalate"),
    ],
    max_iterations=MAX_ITERATIONS,
    after_agent_callback=return_final_response("answer"),
)

deepdive_agent = SequentialAgent(
    name="DeepDive_Agent",
    description="Write a research report on the topic. For addressing ambiguous or open-ended questions.",
    sub_agents=[
        planner_agent,
        synthesizer_refinement_loop,
    ],
)

root_agent = deepdive_agent
