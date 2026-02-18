# Tool Retry Implementation

## Overview

This document describes the retry behavior implementation for Homar's tool calls, as specified in issue [allow homar to retry tools].

## Implementation Details

### 1. Retry Configuration

All API tools in `src/homar.py` now have retry configuration:

```python
@homar.tool(retries=3)
async def todoist_api(ctx: RunContext[MyDeps], command: str) -> str:
    ...
```

The following tools have `retries=3`:
- `todoist_api`
- `home_assistant_api`
- `image_generation_api`
- `grocy_api`
- `google_calendar_api`
- `humblebundle_api`

Delayed message tools have `retries=2`:
- `send_delayed_message`
- `send_scheduled_message`
- `list_scheduled_messages`
- `cancel_scheduled_message`

### 2. ModelRetry Exception

When a tool call fails, it now raises a `ModelRetry` exception with a helpful message:

```python
try:
    r = await todoist_agent.run(command, deps=ctx.deps, usage=ctx.usage)
    return r.output
except Exception as e:
    logger.warning(f"Todoist API tool error: {e}")
    raise ModelRetry(
        f"The Todoist API call failed with error: {str(e)}. "
        f"Please try again with a different approach or rephrase the command."
    )
```

### 3. Retry Behavior

According to PydanticAI documentation:
- When a tool raises `ModelRetry`, the agent automatically resends the request to the model with the retry message
- The model receives the error message and can adjust its approach
- This happens up to `retries` times (e.g., 3 attempts total)
- If all retries are exhausted, `UnexpectedModelBehavior` is raised

### 4. Error Handling in main.py

The Discord bot now catches `UnexpectedModelBehavior` and provides a user-friendly Polish message:

```python
except UnexpectedModelBehavior as e:
    logger.error(f"Tool retry limit exceeded: {e}")
    error_message = "Nie udało mi się wykonać tej operacji pomimo kilku prób. " \
                    "Proszę spróbować ponownie z innym sformułowaniem lub podać więcej szczegółów."
    await thread.send(error_message)
```

## Benefits

1. **Automatic Retry**: Tools automatically retry up to 3 times when they encounter errors
2. **Smart Retry**: The model receives error messages and can adjust its approach on each retry
3. **User-Friendly Errors**: When all retries fail, users receive a clear Polish message instead of raw error details
4. **Logging**: All retry attempts and failures are logged for debugging

## Example Flow

1. User asks: "Turn on the kitchen light"
2. Homar calls `home_assistant_api("Turn on the kitchen light")`
3. First attempt fails with "Device not found"
4. `ModelRetry` is raised with helpful message
5. PydanticAI sends the error back to the model
6. Model tries again with more specific device name
7. Second attempt succeeds, or retries continue up to 3 times
8. If all 3 attempts fail, user sees: "Nie udało mi się wykonać tej operacji pomimo kilku prób..."

## Testing

Tests are provided in `src/homar_retry_test.py` that verify:
- Tools raise `ModelRetry` on errors
- Tools return success on valid responses
- All API tools are properly configured with retries

## References

- PydanticAI Documentation: https://ai.pydantic.dev/tools-advanced#explicit-retry-handling
- Issue: allow homar to retry tools
