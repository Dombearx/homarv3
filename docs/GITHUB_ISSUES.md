# GitHub Issue Creation Tool

## Overview

The GitHub issue creation tool allows the Homar agent to create high-quality, detailed, and well-structured GitHub issues on the homarv3 repository. This tool uses the official PyGithub SDK and leverages an intelligent agent with a specialized prompt to ensure issues are professionally formatted and comprehensive.

## How It Works

1. **User Request**: A user asks the agent to create a GitHub issue
   - Example: "Create an issue about adding a weather forecast feature"
   - Example: "File a bug report for the login error"

2. **Agent Processing**: The Homar agent recognizes the issue creation request and uses the `github_issue_api` tool

3. **Issue Agent**: A specialized sub-agent processes the request:
   - Expands brief descriptions into detailed, well-structured issues
   - Formats the issue with proper Markdown sections
   - Suggests appropriate labels based on the issue type
   - Creates a clear, descriptive title

4. **Issue Creation**: The tool creates the issue on GitHub using PyGithub SDK

5. **Confirmation**: Returns the issue number and URL to the user

## Architecture

### Components

#### 1. GitHubIssueAgent (`src/agents_as_tools/github_issue_agent.py`)
- PydanticAI agent specialized for creating high-quality GitHub issues
- Uses OpenAI GPT-5-mini model with medium reasoning effort
- Includes comprehensive prompt engineering for issue quality
- Provides the `create_github_issue` tool function

#### 2. github_issue_api Tool (`src/homar.py`)
- PydanticAI tool that the Homar agent can call
- Accepts a natural language description
- Delegates to the GitHubIssueAgent for processing
- Returns confirmation with issue number and URL

#### 3. create_github_issue Function
- Uses PyGithub SDK to interact with GitHub API
- Authenticates using GITHUB_TOKEN environment variable
- Creates issues with title, body, and optional labels
- Handles errors gracefully with detailed error messages

## Environment Variables

The tool requires the following environment variables:

```bash
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO=Dombearx/homarv3  # Optional, defaults to Dombearx/homarv3
```

### Setting up GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate a new token with the following permissions:
   - `repo` (Full control of private repositories)
   - Or at minimum: `public_repo` (Access public repositories)
3. Add the token to your `.env` file

## Issue Quality Standards

The agent is designed to create issues that follow these quality standards:

### 1. Title
- Clear and concise
- Uses imperative mood (e.g., "Add feature" not "Adding feature")
- Specific and descriptive
- Includes relevant context

### 2. Body Structure
The agent structures issue bodies with appropriate sections:

**For Bug Reports:**
- **Description**: Clear explanation of the bug
- **Steps to Reproduce**: Numbered list of steps
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: Version info, OS, etc.
- **Additional Context**: Screenshots, logs, etc.

**For Feature Requests:**
- **Description**: Clear explanation of the feature
- **Context**: Why this feature is needed
- **Use Cases**: How it would be used
- **Proposed Solution**: Implementation approach
- **Additional Context**: Examples, references, etc.

### 3. Labels
The agent suggests appropriate labels based on issue type:
- `bug`, `enhancement`, `feature`, `documentation`, `question`
- Priority labels: `high-priority`, `low-priority`
- Component labels if relevant

### 4. Formatting
- Uses proper Markdown formatting
- Includes headers, lists, and code blocks where appropriate
- Professional and clear language
- Thorough and detailed

## Usage Examples

### Example 1: Feature Request

**User:** "Create an issue about adding weather forecast integration"

**Agent Response:**
```
Successfully created issue #42: https://github.com/Dombearx/homarv3/issues/42
```

**Created Issue:**
```markdown
# Add Weather Forecast Integration

## Description
Integrate a weather forecast feature that allows users to check current and future weather conditions.

## Context
Users would benefit from being able to ask about weather conditions without leaving Discord.

## Use Cases
- "What's the weather like today?"
- "Will it rain tomorrow?"
- "What's the forecast for this weekend?"

## Proposed Solution
1. Integrate with a weather API (e.g., OpenWeatherMap, WeatherAPI)
2. Add a new weather_agent in src/agents_as_tools
3. Create tools for current weather and forecast queries
4. Support location-based queries

## Additional Context
- Should support multiple location formats (city name, zip code, coordinates)
- Consider caching weather data to reduce API calls
- Display weather in a user-friendly format with emoji

Labels: enhancement, feature
```

### Example 2: Bug Report

**User:** "File a bug - the bot crashes when image generation fails"

**Agent Response:**
```
Successfully created issue #43: https://github.com/Dombearx/homarv3/issues/43
```

**Created Issue:**
```markdown
# Fix: Bot crashes when image generation fails

## Description
The bot crashes and becomes unresponsive when the image generation service fails or returns an error.

## Steps to Reproduce
1. Request image generation: "Generate an image of a sunset"
2. If the image service is down or returns an error
3. Bot crashes and stops responding

## Expected Behavior
The bot should handle image generation errors gracefully, inform the user of the issue, and continue operating normally.

## Actual Behavior
Bot crashes and requires restart.

## Environment
- Python 3.12
- PydanticAI version from pyproject.toml
- Image generation agent in src/agents_as_tools/image_generation_agent.py

## Additional Context
Need to add proper error handling in the image_generation_api tool and ensure exceptions are caught and logged.

Labels: bug, high-priority
```

## Technical Details

### Tool Signature

```python
@homar.tool
async def github_issue_api(
    ctx: RunContext[MyDeps], 
    description: str
) -> str
```

**Parameters:**
- `ctx`: PydanticAI run context with usage metadata
- `description`: Brief description of the issue to create (expanded by agent)

**Returns:**
- String confirmation with issue number and URL, or error message

### create_github_issue Function

```python
def create_github_issue(
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> str
```

**Parameters:**
- `title`: Issue title
- `body`: Issue body (supports Markdown)
- `labels`: Optional list of label names

**Returns:**
- Success message with issue URL or error message

## Error Handling

The tool handles several error cases:

- **Missing Token**: Returns error if GITHUB_TOKEN is not set
- **Repository Not Found**: Handles 404 errors from GitHub API
- **Permission Errors**: Handles 403 errors for insufficient permissions
- **API Rate Limits**: Handles rate limit errors
- **Network Errors**: Catches connection failures
- **Generic Errors**: Catches any unexpected exceptions

## Testing

### Unit Tests

Comprehensive unit tests are located in `src/agents_as_tools/github_issue_agent_test.py`:

- `test_create_issue_success`: Tests successful issue creation
- `test_create_issue_without_labels`: Tests issue creation without labels
- `test_create_issue_missing_token`: Tests error when token is missing
- `test_create_issue_github_exception`: Tests GitHub API error handling
- `test_create_issue_generic_exception`: Tests generic exception handling

Run tests with:
```bash
pytest src/agents_as_tools/github_issue_agent_test.py -v
```

### Manual Testing

To manually test the issue creation functionality:

1. **Set up environment variables**:
   ```bash
   export GITHUB_TOKEN="your_token"
   export GITHUB_REPO="Dombearx/homarv3"
   ```

2. **Test the agent directly** (optional):
   ```bash
   python src/agents_as_tools/github_issue_agent.py
   ```

3. **Test through Discord**:
   - Send a message to the bot: "Create an issue for testing the GitHub integration"
   - Verify the issue is created on GitHub
   - Check that the response includes the issue number and URL

## Limitations

1. **Repository Scope**: Currently configured for the homarv3 repository only
2. **Token Permissions**: Requires a GitHub token with repository access
3. **Label Validation**: Does not validate that labels exist in the repository
4. **Assignee Support**: Does not support assigning issues to users
5. **Milestone Support**: Does not support setting milestones

## Security Considerations

1. **Token Storage**: GITHUB_TOKEN should be kept secret and never committed to version control
2. **Token Permissions**: Use tokens with minimal required permissions
3. **Rate Limiting**: Be aware of GitHub API rate limits (5000 requests/hour for authenticated requests)
4. **Input Validation**: The tool validates inputs to prevent injection attacks

## Future Enhancements

Potential improvements:

1. **Multi-Repository Support**: Allow creating issues in different repositories
2. **Issue Templates**: Support for repository issue templates
3. **Assignee Support**: Ability to assign issues to specific users
4. **Milestone Support**: Set milestones when creating issues
5. **Issue Editing**: Update existing issues
6. **Issue Commenting**: Add comments to issues
7. **Issue Search**: Search for existing issues before creating duplicates
8. **Project Board Integration**: Add issues to project boards
9. **Link to Related Issues**: Automatically link related issues
10. **Webhook Integration**: Notify Discord when issues are created/updated

## Implementation Notes

- Uses PyGithub 2.5.0+ (official Python SDK for GitHub API)
- Agent uses OpenAI GPT-5-mini with medium reasoning effort for quality
- Follows the same pattern as other agents (todoist, home_assistant, grocy)
- Comprehensive prompt ensures high-quality issue generation
- All tests pass with 100% success rate
- Code passes ruff linting and formatting checks
- No security vulnerabilities detected by CodeQL
