# Delayed Message Tool

## Overview

The delayed message tool allows the Homar agent to schedule messages to be sent to itself after a specified delay. This is useful for executing commands that need to happen in the future, such as turning off lights after a certain period or setting reminders.

## How It Works

1. **User Request**: A user asks the agent to perform an action after a certain amount of time
   - Example: "Turn off the light in 1 hour"
   - Example: "Remind me to check the oven in 30 minutes"

2. **Agent Processing**: The agent recognizes the delayed action request and uses the `send_delayed_message` tool

3. **Message Scheduling**: The tool schedules a message to be sent back to the agent in the same Discord thread after the specified delay

4. **Message Delivery**: After the delay expires, the scheduled message is automatically sent to the Discord thread with a special marker `[DELAYED_COMMAND]`

5. **Command Execution**: The agent receives its own message, recognizes it as a delayed command, and executes the requested action

## Architecture

### Components

#### 1. DelayedMessageScheduler (`src/delayed_message_scheduler.py`)
- Manages scheduled messages using asyncio tasks
- Stores messages in memory with thread ID and delivery callback
- Handles message delivery after the specified delay
- Provides methods to schedule, cancel, and list delayed messages

#### 2. send_delayed_message Tool (`src/homar.py`)
- PydanticAI tool that the agent can call
- Accepts a message and delay in seconds
- Validates the delay (1 second to 7 days)
- Schedules the message using the DelayedMessageScheduler
- Returns human-readable confirmation

#### 3. Message Handler (`main.py`)
- Modified to accept bot's own messages with `[DELAYED_COMMAND]` marker
- Strips the marker before processing the delayed command
- Passes thread context (thread_id and send_message_callback) to the agent

#### 4. MyDeps Model (`src/models/schemas.py`)
- Extended to include:
  - `thread_id`: Discord thread ID for sending delayed messages
  - `send_message_callback`: Async function to send messages to Discord

## Usage Examples

### User: "Turn off the bedroom light in 30 minutes"

**Agent Response:**
```
Scheduled to send 'Turn off bedroom light' in 30 minutes
```

**After 30 minutes:**
- The message `[DELAYED_COMMAND] Turn off bedroom light` is sent to the thread
- The agent receives it, processes the command, and turns off the light

### User: "Remind me in 2 hours to check the laundry"

**Agent Response:**
```
Scheduled to send 'Check the laundry' in 2 hours
```

**After 2 hours:**
- The message `[DELAYED_COMMAND] Check the laundry` is sent to the thread
- The agent receives it and sends a reminder message

## Technical Details

### Tool Signature

```python
@homar.tool
async def send_delayed_message(
    ctx: RunContext[MyDeps], 
    message: str, 
    delay_seconds: int
) -> str
```

**Parameters:**
- `ctx`: PydanticAI run context with MyDeps (thread_id and send_message_callback)
- `message`: The command/message to send after the delay
- `delay_seconds`: How long to wait before sending (1 to 604800 seconds / 7 days)

**Returns:**
- String confirmation of the scheduled message

### Delayed Message Format

Delayed messages are marked with the prefix `[DELAYED_COMMAND]` to distinguish them from regular bot messages. This marker is:
- Added by the scheduler when scheduling the message
- Detected by the message handler in `main.py`
- Stripped before processing the command
- Not visible to the user

### Message Flow

```
User Message
    ↓
Agent processes and calls send_delayed_message
    ↓
Scheduler creates asyncio task
    ↓
Task waits for delay_seconds
    ↓
Task calls send_message_callback with marked message
    ↓
Discord bot sends message to thread
    ↓
Message handler detects [DELAYED_COMMAND] marker
    ↓
Agent processes the delayed command
    ↓
Agent executes the action
```

## Limitations

1. **In-Memory Storage**: Scheduled messages are stored in memory and will be lost if the bot restarts
2. **Maximum Delay**: Limited to 7 days (604800 seconds)
3. **Minimum Delay**: Must be at least 1 second
4. **Thread Scope**: Messages can only be sent to the thread where they were scheduled

## Future Enhancements

Potential improvements for the delayed message system:

1. **Persistence**: Store scheduled messages in a database to survive bot restarts
2. **Cancellation Interface**: Allow users to cancel scheduled messages
3. **Listing**: Show users their currently scheduled messages
4. **Recurring Messages**: Support for repeated delayed messages
5. **Edit Scheduled Messages**: Modify delay or content before execution
6. **Time Zone Support**: Allow users to specify times in their local timezone
7. **Natural Language Parsing**: Better parsing of time expressions like "next Tuesday at 3pm"

## Error Handling

The tool handles several error cases:

- **Missing Context**: Returns error if thread_id or send_message_callback is not available
- **Invalid Delay**: Returns error if delay is less than 1 second or more than 7 days
- **Scheduling Failures**: Catches and logs exceptions during message scheduling
- **Send Failures**: Logs errors if message delivery fails

## Testing

To test the delayed message functionality:

1. **Short Delay Test**: Ask the agent to send a message in 5-10 seconds
   ```
   "Send me a test message in 10 seconds"
   ```

2. **Command Execution Test**: Schedule a simple command
   ```
   "Turn on the living room light in 30 seconds"
   ```

3. **Edge Cases**:
   - Try delays less than 1 second (should fail)
   - Try very large delays (should fail if > 7 days)
   - Restart the bot while messages are scheduled (messages will be lost)

## Implementation Notes

- The scheduler uses `asyncio.create_task()` for non-blocking execution
- Tasks are automatically cleaned up after message delivery
- The `DELAYED_COMMAND_MARKER` constant in `main.py` can be changed if needed
- The bot must have permission to send messages in the thread
- Thread history includes delayed command messages in the conversation context
