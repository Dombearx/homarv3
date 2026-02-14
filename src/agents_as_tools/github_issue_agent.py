from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from github import Github, Auth, GithubException
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_ISSUE_AGENT_PROMPT = """
You are a GitHub issue creation specialist. Your role is to help create high-quality, detailed, and well-structured GitHub issues.

When creating an issue, you should:

1. **Title**: Create a clear, concise, and descriptive title that summarizes the issue
   - Use imperative mood (e.g., "Add feature" not "Adding feature")
   - Be specific and descriptive
   - Include relevant context (e.g., component name, error type)

2. **Body**: Structure the issue body with appropriate sections:
   - **Description**: Clear explanation of the issue/feature request
   - **Context**: Background information and use cases
   - **Steps to Reproduce** (for bugs): Numbered list of steps
   - **Expected Behavior**: What should happen
   - **Actual Behavior** (for bugs): What actually happens
   - **Proposed Solution** (for features): How to implement
   - **Additional Context**: Screenshots, logs, environment details, etc.
   - Use Markdown formatting for better readability

3. **Labels**: Suggest appropriate labels based on the issue type:
   - bug, enhancement, feature, documentation, question, etc.
   - Include priority labels if relevant (high-priority, low-priority)
   - Include component/area labels if relevant

4. **Quality Standards**:
   - Be thorough and provide all necessary details
   - Use proper Markdown formatting (headers, lists, code blocks)
   - Include examples where appropriate
   - Be professional and clear
   - Avoid ambiguity

When the user provides a brief description, expand it into a comprehensive, well-formatted issue.
If important details are missing, use reasonable defaults or mark sections as needing clarification.

Always return the issue creation result including the issue number and URL.
"""

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="medium",
    openai_reasoning_summary="verbose",
)

github_issue_agent = Agent(
    "openai:gpt-5-mini",
    instructions=GITHUB_ISSUE_AGENT_PROMPT,
    model_settings=settings,
    retries=3,
)


@github_issue_agent.tool_plain
def create_github_issue(
    title: str,
    body: str,
    labels: list[str] = None,
) -> str:
    """Create a new GitHub issue in the homarv3 repository.

    Args:
        title: The title of the issue
        body: The body/description of the issue (supports Markdown)
        labels: List of label names to apply to the issue (optional)

    Returns:
        A message indicating success or failure with the issue URL
    """
    # Get GitHub credentials from environment
    github_token = os.getenv("GITHUB_TOKEN")
    github_repo = os.getenv("GITHUB_REPO", "Dombearx/homarv3")

    if not github_token:
        return "Error: GITHUB_TOKEN environment variable is not set"

    try:
        # Authenticate with GitHub
        auth = Auth.Token(github_token)
        g = Github(auth=auth)

        # Get the repository
        repo = g.get_repo(github_repo)

        # Create the issue
        issue = repo.create_issue(
            title=title,
            body=body,
            labels=labels if labels else [],
        )

        return f"Successfully created issue #{issue.number}: {issue.html_url}"

    except GithubException as e:
        return f"GitHub API error: {e.status} - {e.data.get('message', str(e))}"
    except Exception as e:
        return f"Error creating issue: {str(e)}"


if __name__ == "__main__":
    import asyncio

    async def main():
        r = await github_issue_agent.run(
            "Create an issue about adding a new weather forecast feature that would allow users to check weather conditions",
        )
        print("Output:", r.output)

    asyncio.run(main())
