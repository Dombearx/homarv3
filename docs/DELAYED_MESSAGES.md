# Delayed and Scheduled Message Tools

## Tools Available

The delayed and scheduled message system provides the following tools for the Homar agent:

1. **send_delayed_message**: Schedule a message with a delay in seconds/minutes/hours
2. **send_scheduled_message**: Schedule a message at a specific date and time
3. **list_scheduled_messages**: List all pending scheduled messages
4. **cancel_scheduled_message**: Cancel a previously scheduled message

## How It Works

### Delayed Messages (Relative Time)

1. **User Request**: A user asks the agent to perform an action after a certain amount of time
   - Example: "Turn off the light in 1 hour"
   - Example: "Remind me to check the oven in 30 minutes"

2. **Agent Processing**: The agent recognizes the delayed action request and uses the `send_delayed_message` tool

3. **Message Scheduling**: The tool schedules a message to be sent back to the agent in the same Discord thread after the specified delay

4. **Message Delivery**: After the delay expires, the scheduled message is automatically sent to the Discord thread with a special marker `[DELAYED_COMMAND]`

5. **Command Execution**: The agent receives its own message, recognizes it as a delayed command, and executes the requested action

### Scheduled Messages (Absolute Time)

1. **User Request**: A user asks the agent to perform an action at a specific date and time
   - Example: "Turn off the light at 10pm"
   - Example: "Remind me on December 25th at 9am"

2. **Agent Processing**: The agent recognizes the scheduled action request and uses the `send_scheduled_message` tool

3. **Message Scheduling**: The tool calculates the delay until the specified time and schedules a message

4. **Message Delivery**: When the scheduled time arrives, the message is automatically sent with the `[DELAYED_COMMAND]` marker

5. **Command Execution**: The agent receives and processes the scheduled command

## Architecture

### Components

#### 1. DelayedMessageScheduler (`src/delayed_message_scheduler.py`)
- Manages scheduled messages using asyncio tasks
- Stores messages in memory with thread ID and delivery callback
- Handles message delivery after the specified delay or at the scheduled time
- Provides methods to schedule, cancel, and list delayed messages
- Supports both relative delays (seconds) and absolute times (datetime)

#### 2. send_delayed_message Tool (`src/homar.py`)
- PydanticAI tool that the agent can call
- Accepts a message and delay specified in hours, minutes, and seconds
- Validates the delay (1 second to 7 days)
- Schedules the message using the DelayedMessageScheduler
- Returns human-readable confirmation

#### 3. send_scheduled_message Tool (`src/homar.py`)
- PydanticAI tool that the agent can call
- Accepts a message and a specific date/time string
- Supports multiple datetime formats (ISO 8601, date-only, etc.)
- Validates that the scheduled time is in the future
- Schedules the message using the DelayedMessageScheduler
- Returns human-readable confirmation

#### 4. Message Handler (`main.py`)
- Modified to accept bot's own messages with `[DELAYED_COMMAND]` marker
- Strips the marker before processing the delayed command
- Passes thread context (thread_id and send_message_callback) to the agent

#### 5. MyDeps Model (`src/models/schemas.py`)
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

### User: "Turn off the lights at 10pm"

**Agent Response:**
```
Scheduled to send 'Turn off the lights' on 2026-02-14 at 22:00:00
```

**At 10pm:**
- The message `[DELAYED_COMMAND] Turn off the lights` is sent to the thread
- The agent receives it, processes the command, and turns off the lights

### User: "Remind me on December 25th at 9am to check the oven"

**Agent Response:**
```
Scheduled to send 'Check the oven' on 2024-12-25 at 09:00:00 CET
```

**On December 25th at 9am:**
- The message `[DELAYED_COMMAND] Check the oven` is sent to the thread
- The agent receives it and sends a reminder message

### User: "What actions do I have scheduled?"

**Agent Response:**
```
Found 2 scheduled message(s):

- ID: delayed_1
  Time: 2026-02-16 22:30:00 CET
  Message: Turn off bedroom light

- ID: scheduled_1
  Time: 2026-12-25 09:00:00 CET
  Message: Check the oven
```

### User: "Cancel the scheduled message delayed_1"

**Agent Response:**
```
Successfully cancelled scheduled message: delayed_1
```

The scheduled action for turning off the bedroom light has been removed and will not execute.

### User: "Cancel that reminder"

**Agent Action:**
1. The agent calls `list_scheduled_messages` to see what's scheduled
2. Identifies which message the user is referring to
3. Calls `cancel_scheduled_message` with the appropriate message ID

**Agent Response:**
```
Successfully cancelled scheduled message: scheduled_1
```

## Technical Details

### Tool Signatures

#### send_delayed_message

```python
@homar.tool
async def send_delayed_message(
    ctx: RunContext[MyDeps], 
    message: str, 
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0
) -> str
```

**Parameters:**
- `ctx`: PydanticAI run context with MyDeps (thread_id and send_message_callback)
- `message`: The command/message to send after the delay
- `hours`: Number of hours to wait (0 to 168, default 0)
- `minutes`: Number of minutes to wait (0 to 59, default 0)
- `seconds`: Number of seconds to wait (0 to 59, default 0)
- Total delay must be at least 1 second and at most 7 days (604800 seconds)
- At least one time parameter (hours, minutes, or seconds) must be greater than 0

**Returns:**
- String confirmation of the scheduled message

#### send_scheduled_message

```python
@homar.tool
async def send_scheduled_message(
    ctx: RunContext[MyDeps], 
    message: str, 
    scheduled_datetime: str
) -> str
```

**Parameters:**
- `ctx`: PydanticAI run context with MyDeps (thread_id and send_message_callback)
- `message`: The command/message to send at the scheduled time
- `scheduled_datetime`: ISO 8601 datetime string (e.g., "2024-12-25T09:00:00")
                       Times are interpreted in Europe/Warsaw timezone (CET/CEST)

**Supported datetime formats:**
- `YYYY-MM-DDTHH:MM:SS` (ISO 8601 with T separator)
- `YYYY-MM-DD HH:MM:SS` (space separator)
- `YYYY-MM-DD HH:MM` (without seconds)
- `YYYY-MM-DDTHH:MM` (ISO without seconds)
- `YYYY-MM-DD` (date only, uses 00:00:00)

**Returns:**
- String confirmation of the scheduled message

#### list_scheduled_messages

```python
@homar.tool
async def list_scheduled_messages(ctx: RunContext[MyDeps]) -> str
```

**Purpose:**
Lists all currently scheduled messages that are pending delivery.

**Parameters:**
- `ctx`: PydanticAI run context with MyDeps

**Returns:**
- A formatted list of all scheduled messages with their IDs, scheduled times, and content
- "No scheduled messages pending." if there are no scheduled messages

**Usage:**
Use when the user asks to see pending actions, scheduled messages, or what's coming up.

**Example output:**
```
Found 2 scheduled message(s):

- ID: delayed_1
  Time: 2026-02-16 22:30:00 CET
  Message: Turn off living room light

- ID: scheduled_1
  Time: 2026-02-17 09:00:00 CET
  Message: Remind me to check the mail
```

#### cancel_scheduled_message

```python
@homar.tool
async def cancel_scheduled_message(ctx: RunContext[MyDeps], message_id: str) -> str
```

**Purpose:**
Cancels a previously scheduled message that hasn't been sent yet.

**Parameters:**
- `ctx`: PydanticAI run context with MyDeps
- `message_id`: The ID of the scheduled message to cancel (e.g., "delayed_1" or "scheduled_1")

**Returns:**
- Confirmation that the message was cancelled or an error if not found

**Usage:**
Use when the user wants to cancel a scheduled action. The user can specify the message by its ID (obtained from `list_scheduled_messages`) or by description.

**Examples:**
- "Cancel scheduled message delayed_1"
- "Cancel that reminder"
- "Remove the scheduled action"

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
2. **Maximum Delay**: Limited to 7 days (604800 seconds) for both delayed and scheduled messages
3. **Minimum Delay**: Must be at least 1 second in the future
4. **Thread Scope**: Messages can only be sent to the thread where they were scheduled
5. **Timezone**: All times are interpreted as Europe/Warsaw timezone (CET/CEST). The system automatically handles daylight saving time transitions.

## Timezone Support

As of the latest update, the system now supports timezone-aware datetime handling:

- **Default Timezone**: Europe/Warsaw (CET/CEST)
- **Automatic DST Handling**: The system uses Python's `zoneinfo` module to handle daylight saving time transitions automatically
- **Time Interpretation**: When you schedule an action at "21:22", it will execute at 21:22 in the Europe/Warsaw timezone, regardless of the server's timezone
- **Display Format**: Scheduled times are displayed with timezone information (e.g., "2026-02-16 at 21:22:00 CET")

### Why Europe/Warsaw?

The timezone was chosen based on the Polish language used in Homar's instructions, indicating the primary user base is in Poland.

## Future Enhancements

Potential improvements for the delayed message system:

1. **Persistence**: Store scheduled messages in a database to survive bot restarts
2. **Recurring Messages**: Support for repeated delayed messages
3. **Edit Scheduled Messages**: Modify delay or content before execution
4. **Configurable Timezone**: Allow users to configure their preferred timezone
5. **Natural Language Parsing**: Better parsing of time expressions like "next Tuesday at 3pm"

## Error Handling

The tools handle several error cases:

### send_delayed_message
- **Missing Context**: Returns error if thread_id or send_message_callback is not available
- **Invalid Delay**: Returns error if delay is less than 1 second or more than 7 days
- **Scheduling Failures**: Catches and logs exceptions during message scheduling
- **Send Failures**: Logs errors if message delivery fails

### send_scheduled_message
- **Missing Context**: Returns error if thread_id or send_message_callback is not available
- **Invalid Format**: Returns error if datetime string cannot be parsed
- **Past Time**: Returns error if scheduled time is not in the future
- **Maximum Delay**: Returns error if scheduled time is more than 7 days in the future
- **Scheduling Failures**: Catches and logs exceptions during message scheduling
- **Send Failures**: Logs errors if message delivery fails

### list_scheduled_messages
- **No Scheduled Messages**: Returns friendly message when no messages are scheduled
- **Timezone Display**: Shows scheduled times with timezone information for clarity

### cancel_scheduled_message
- **Message Not Found**: Returns error message if the specified message_id doesn't exist
- **Cancellation Success**: Immediately removes the message from the scheduler
- **Already Sent**: If the message has already been sent, returns not found error

## Testing

To test the delayed and scheduled message functionality:

### Delayed Messages

1. **Short Delay Test**: Ask the agent to send a message in 5-10 seconds
   ```
   "Send me a test message in 10 seconds"
   ```

2. **Command Execution Test**: Schedule a simple command
   ```
   "Turn on the living room light in 30 seconds"
   ```

### Scheduled Messages

1. **Near Future Test**: Ask the agent to send a message at a specific time in the next few minutes
   ```
   "Send me a test message at 3:45pm"
   ```

2. **Date and Time Test**: Schedule a command for a specific date and time
   ```
   "Turn on the living room light on December 25th at 9am"
   ```

3. **Date Only Test**: Schedule a message for a specific date
   ```
   "Remind me to check the mail on 2024-12-25"
   ```

### Edge Cases
- Try delays less than 1 second (should fail)
- Try very large delays (should fail if > 7 days)
- Try scheduling in the past (should fail)
- Restart the bot while messages are scheduled (messages will be lost)

### New Tools Testing

1. **List Scheduled Messages**: Schedule a few messages then ask
   ```
   "What messages are scheduled?"
   ```

2. **Cancel Message**: Schedule a message, list it to get the ID, then cancel it
   ```
   "Schedule a message in 5 minutes to turn off the light"
   "What messages are scheduled?"  # Get the message ID
   "Cancel scheduled message delayed_1"
   ```

3. **Timezone Verification**: Schedule a message for a specific time and verify it executes at the correct time in Europe/Warsaw timezone
   ```
   "Turn on the light at 21:22"  # Should execute at 21:22 CET/CEST, not UTC
   ```

## Implementation Notes

- The scheduler uses `asyncio.create_task()` for non-blocking execution
- Tasks are automatically cleaned up after message delivery
- The `DELAYED_COMMAND_MARKER` constant in `main.py` can be changed if needed
- The bot must have permission to send messages in the thread
- Thread history includes delayed command messages in the conversation context
