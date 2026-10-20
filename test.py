# Before running the sample:
#    python -m pip install "azure-ai-projects>=2.7.0" azure-identity

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import VersionRefIndicator

endpoint = "https://foundry-cua-resource.services.ai.azure.com/api/projects/foundry-cua"
agent_name = "investiq-maf-harness"
agent_version = "6"

def run_question(question: str) -> str:
    if not isinstance(question, str) or not question.strip() or len(question) > 4000:
        raise ValueError("Enter a question containing 1-4000 characters.")

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=endpoint,
            credential=credential,
            allow_preview=True,
            connection_timeout=15,
            read_timeout=120,
            retry_total=0,
        ) as project_client,
    ):
        session = project_client.agents.create_session(
            agent_name=agent_name,
            version_indicator=VersionRefIndicator(agent_version=agent_version),
        )
        try:
            with project_client.get_openai_client(
                agent_name=agent_name, timeout=120, max_retries=0,
            ) as openai_client:
                response = openai_client.responses.create(
                    input=question.strip(),
                    extra_body={"agent_session_id": session.agent_session_id},
                )

            lines = [
                f"Agent: {agent_name}, version: {agent_version}",
                f"Created session: {session.agent_session_id}",
                f"\nResponse:\n{response.output_text}",
                "\nTool calls returned by the endpoint:",
            ]
            tool_calls = [item for item in response.output if item.type == "function_call"]
            lines.extend(f"- {call.name}: {call.arguments}" for call in tool_calls)
            if not tool_calls:
                lines.append("No tool calls were exposed in this response; check Foundry traces for execution details.")

            lines.append("\nSkill-loading calls returned by the endpoint:")
            skill_calls = [call for call in tool_calls if call.name == "load_skill"]
            lines.extend(f"- {call.arguments}" for call in skill_calls)
            if not skill_calls:
                lines.append("No skill-loading calls were exposed; this does not prove that no skill was used.")
            return "\n".join(lines)
        finally:
            project_client.agents.delete_session(
                agent_name=agent_name,
                session_id=session.agent_session_id,
            )


if __name__ == "__main__":
    print(run_question(
        "Analyze QQQM using its latest available quote, fundamentals, and recent news. "
        "Explain the main business drivers and risks, and cite your sources. "
        "Don't ask follow-up questions, proceed with your analysis."
    ))