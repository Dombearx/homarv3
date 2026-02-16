# Tool Approval Mechanism

This document describes the tool approval mechanism implemented in Homarv3, which allows certain tools to require user confirmation before executing.

## Overview

The approval mechanism uses PydanticAI's `DeferredToolRequests` feature to pause agent execution and request user approval via Discord UI (buttons) before executing specific tools.

## How It Works

### 1. Tool Configuration

Tools can be marked as requiring approval in two ways:

#### Static Approval (Always Required)
Use the `requires_approval=True` parameter in the tool decorator:

```python
@homar.tool_plain(requires_approval=True)
def delete_file(path: str) -> str:
    """Delete a file - always requires user approval."""
    return f"File {path} deleted"
```

#### Dynamic Approval (Conditional)
Raise `ApprovalRequired` exception based on runtime conditions:

```python
from pydantic_ai import ApprovalRequired, RunContext

@homar.tool
def update_file(ctx: RunContext, path: str, content: str) -> str:
    """Update a file - requires approval for protected files."""
    PROTECTED_FILES = {'.env', 'config.yml'}
    
    if path in PROTECTED_FILES and not ctx.tool_call_approved:
        raise ApprovalRequired(metadata={'reason': 'protected file'})
    
    return f"File {path} updated"
```

### 2. Approval Flow

When a tool requiring approval is called:

1. **Agent Pauses**: The agent returns a `DeferredToolRequests` object instead of a string response
2. **Discord UI**: A message is sent to the thread with:
   - Tool name
   - Parameters being used
   - Accept ✅ and Reject ❌ buttons
3. **User Action**: User clicks either button
4. **Agent Resumes**: Agent continues with the approval results
5. **Final Response**: Agent provides the final response incorporating the tool result (if approved) or explaining the rejection

### 3. User Experience

#### Approval Request Message
```
🔔 **Tool Approval Required**
The following tools require your confirmation:

**Tool:** `test_discord_approval`
**Parameters:**
  • test_parameter: `test_value`

**Please approve or reject this action:**

[✅ Accept] [❌ Reject]
```

#### After Approval
The message is updated with the user's decision:
```
[previous content]

**✅ APPROVED by user**
```

#### After Rejection
```
[previous content]

**❌ REJECTED by user**
```

#### Timeout (5 minutes)
```
[previous content]

**⏱️ TIMEOUT - Request expired**
```

### 4. Implementation Details

#### Files Modified
- `src/homar.py`: Added `DeferredToolRequests` output type and test tool
- `src/discord_approval.py`: Discord UI components and approval handling
- `main.py`: Integration of approval flow into message processing

#### Key Components

**ApprovalView** (`src/discord_approval.py`)
- Discord View with Accept/Reject buttons
- Handles button clicks and user interaction
- 5-minute timeout for responses

**request_approval()** (`src/discord_approval.py`)
- Sends approval request message with buttons
- Waits for user response
- Returns `DeferredToolResults` with approval/rejection

**Pending Approvals Storage**
- Global dictionary mapping message IDs to approval data
- Enables button handlers to access the right approval context
- Cleaned up after approval, rejection, or timeout

## Test Tool

A test tool is included for verifying the approval mechanism:

```python
@homar.tool_plain(requires_approval=True)
def test_discord_approval(test_parameter: str) -> str:
    """Test tool for Discord approval mechanism."""
    return f"Test tool executed successfully with parameter: {test_parameter}"
```

### Usage Example

In Discord, send:
```
@Homar please run the test approval tool with parameter "hello"
```

The bot will:
1. Recognize the tool needs approval
2. Display the approval UI
3. Wait for your response
4. Execute the tool (if approved) and return the result

## Technical Notes

### Async Flow
The approval mechanism uses asyncio Futures to pause and resume execution:
1. Future is created when approval is requested
2. Button handler sets the future result
3. `request_approval()` awaits the future

### Timeout Handling
- Default timeout: 5 minutes (300 seconds)
- On timeout, all pending tools are automatically rejected
- Timeout message is displayed to user

### Multiple Tools
If multiple tools require approval in a single agent run:
- All are displayed in one approval request
- All must be approved or rejected together (current MVP)
- Future enhancement: Individual approval per tool

### Error Handling
- Expired/removed approvals return appropriate error messages
- Timeout automatically rejects all pending tools
- Exceptions are logged with detailed context

## Testing

Comprehensive tests are provided in `src/discord_approval_test.py`:
- Message formatting
- Timeout handling
- Cleanup logic
- Integration scenarios

Run tests:
```bash
pytest src/discord_approval_test.py -v
```

## Future Enhancements

Potential improvements for the approval mechanism:
1. Individual approval for multiple tools (not batch)
2. Configurable timeout per tool type
3. Approval history/audit log
4. Role-based approval requirements
5. Custom approval messages per tool
6. Preview of tool effects before approval

## Security Considerations

- All sensitive parameters are displayed to the user (consider masking in future)
- Parameter values are truncated at 100 characters for display
- Approval state is stored in-memory (consider persistence for HA)
- Timeout prevents indefinite pending approvals
- Only the thread where approval was requested can respond (via Discord's message context)
