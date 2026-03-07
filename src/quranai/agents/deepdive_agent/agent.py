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


def conditionally_return_final_response(callback_context: CallbackContext):
    status = callback_context.session.state.get("plan_feedback", "").strip()
    should_stop = status == LOOP_COMPLETION_PHRASE
    if should_stop:
        final_answer = callback_context.state["plan"]
        logging.info(callback_context.state.to_dict())
        logging.info(
            f"In {callback_context.agent_name} returning final answer: {final_answer}"
        )
        return types.Content(parts=[types.Part(text=final_answer)], role="model")


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
                content=types.Content(
                    parts=[types.Part(text=final_answer)], role="model"
                ),
            )
        else:
            yield Event(
                author=self.name,
                actions=EventActions(escalate=should_stop, skip_summarization=True),
            )


check_status_and_escalate = CheckStatusAndEscalate(name="CheckStatusAndEscalate")


initial_plan_writer = Agent(
    model="gemini-2.5-flash",
    name="Initial_Plan_Writer",
    description="Make initial plan for the research topic.",
    include_contents="none",
    instruction=f"""
        Use the provided tools to conduct meta-analysis of sources and formulate a research plan.

        Topic:
        ```
        {{query}}
        ```
        Important:
        -  Write in imperative to-do list format.
        - Only output the plan. Do not add explanations or any other text.
        """,
    tools=[tools.get_topics_for_query],
    output_key="plan",
)

planner_critic_in_loop = Agent(
    model="gemini-2.5-flash",
    name="Planner_Critic",
    description="Review the plan created by the planner agent.",
    include_contents="none",
    instruction=f"""
        Review the following research plan for the topic.
        If it is sufficient, respond *exactly* and *only* with {LOOP_COMPLETION_PHRASE}
        If not, provide feedback on how to improve it.
        Topic:
        ```
        {{query}}
        ```
        Plan:
        ```
        {{plan}}
        ```
        """,
    tools=[],
    output_key="plan_feedback",
)

planner_in_loop = Agent(
    model="gemini-2.5-flash",
    name="Plan_Writer",
    description="Iterate on the research plan given the query and feedback.",
    include_contents="none",
    instruction=f"""
        Use the provided tools to refine research plan for the research topic:
        ```
        {{query}}
        ```
        Current plan:
        ```
        {{plan}}
        ```
        Feedback on current plan (if any):
        ```
        {{plan_feedback}}
        ```
        IMPORTANT:
        - Write in imperative to-do list format.
        - Do not add explanations in your response.
        """,
    tools=[tools.get_topics_for_query],
    output_key="plan",
)

planner_refinement_loop = LoopAgent(
    name="Planner_Refinement_Loop",
    description="Iteratively refine the research plan until it is sufficient.",
    sub_agents=[planner_critic_in_loop, check_status_and_escalate, planner_in_loop],
    max_iterations=MAX_ITERATIONS,
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
    model="gemini-2.5-flash",
    name="Synthesizer",
    description="Synthesize the research findings into a final answer with citations.",
    instruction=(
        "Use the provided tools to synthesize the research findings into a final answer with citations:\n\n"
        "Plan: {plan}\n"
    ),
    tools=[],
    output_key="answer",
)

synthesizer_critic_in_loop = Agent(
    model="gemini-2.5-flash",
    name="Synthesizer_Critic",
    description="Review the synthesized answer.",
    instruction=(
        "Review the following synthesized answer with respect to the research plan. If it is sufficient, call the exit_loop tool. "
        "If not, provide feedback on how to improve it. "
        "Synthesized Answer: \n"
        "```\n"
        "{answer}"
        "\n```\n"
        "Research Plan: {plan}"
    ),
    tools=[exit_loop],
    output_key="answer_feedback",
)


root_agent = planner_agent
