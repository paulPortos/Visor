from agno.agent import Agent
from agno.models.google import Gemini
from django.conf import settings

from multi_agent.agents.llm_agent_run_with_retry import llm_agent_run_with_retry
from multi_agent.agents.sr_dev.prompts.senior_dev_agent_instructions import senior_dev_agent_instructions
from multi_agent.agents.sr_dev.prompts.senior_dev_session_memory_context_build import (
    senior_dev_session_memory_context_build,
)


def senior_dev_agent_run(*, session, user_message, tools):
    """Executes the Senior Dev agent to process messages with repository tool access."""
    model = Gemini(
        id=settings.SR_DEV_AGENT_MODEL,
        api_key=settings.GEMINI_API_KEY,
    )

    agent = Agent(
        name='Senior Dev Agent',
        model=model,
        session_id=f'sr_dev:{session.id}',
        tools=tools,
        markdown=False,
        tool_call_limit=settings.SR_DEV_TOOL_CALL_LIMIT,
        instructions=senior_dev_agent_instructions(),
        debug_mode=True,
    )
    prompt = (
        f'Project ID: {session.project_id}\n'
        f'Git commit SHA: {session.commit_sha}\n'
        f'Branch label: {session.branch_name or "not provided"}\n'
        'Current session conversation so far:\n'
        f'{senior_dev_session_memory_context_build(session=session, before_message=user_message)}\n'
        f'User message:\n{user_message.text_content}'
    )
    response = llm_agent_run_with_retry(agent, prompt, agent_name='Senior Dev Agent')
    return str(getattr(response, 'content', response) or '').strip()
