# Testing the Tool Approval Mechanism

This guide explains how to manually test the tool approval mechanism in Homarv3.

## Prerequisites

1. Discord bot is running and connected to a server
2. You have access to a Discord channel where the bot is active
3. The bot has permission to create threads and add reactions/buttons

## Test Scenario 1: Basic Approval Flow

### Step 1: Trigger the Test Tool

In any Discord channel where Homar is active, send:

```
@Homar please run the test approval tool with parameter "hello world"
```

or

```
@Homar call test_discord_approval with test_parameter "my test value"
```

### Expected Behavior:

1. **Initial Typing Indicator**: Bot shows typing indicator
2. **Approval Request Message**: Bot sends a message like:

```
🔔 **Tool Approval Required**
The following tools require your confirmation:

**Tool:** `test_discord_approval`
**Parameters:**
  • test_parameter: `hello world`

**Please approve or reject this action:**

[✅ Accept] [❌ Reject]
```

3. **Buttons Visible**: Two buttons are displayed below the message

### Step 2: Test Approval

Click the **✅ Accept** button.

### Expected Behavior:

1. **Message Updated**: The approval message is updated with:
```
[previous content]

**✅ APPROVED by user**
```

2. **Final Response**: Bot sends a new message:
```
Test tool executed successfully with parameter: hello world
```

## Test Scenario 2: Rejection Flow

### Step 1: Trigger the Tool Again

```
@Homar please run the test approval tool with parameter "test rejection"
```

### Step 2: Test Rejection

Click the **❌ Reject** button.

### Expected Behavior:

1. **Message Updated**:
```
[previous content]

**❌ REJECTED by user**
```

2. **Final Response**: Bot acknowledges the rejection, e.g.:
```
The action was rejected by the user.
```
or
```
Nie udało się wykonać polecenia, użytkownik odrzucił akcję.
```

## Test Scenario 3: Timeout

### Step 1: Trigger the Tool

```
@Homar test the approval mechanism with parameter "timeout test"
```

### Step 2: Wait (Do NOT Click Any Button)

Wait for 5 minutes without clicking any button.

### Expected Behavior:

After 5 minutes:

1. **Message Updated**:
```
[previous content]

**⏱️ TIMEOUT - Request expired**
```

2. **Buttons Disabled**: The buttons are no longer clickable
3. **Final Response**: Bot sends a timeout/error message

## Test Scenario 4: Multiple Parameters

Test with more complex parameters:

```
@Homar run test_discord_approval with a very long parameter value: Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
```

### Expected Behavior:

The approval message should truncate long values:
```
**Parameters:**
  • test_parameter: `Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ...`
```

But the actual full value is preserved and used when approved.

## Test Scenario 5: Error Cases

### Test 5a: Expired Approval

1. Trigger approval
2. Wait for timeout (5 min)
3. Try clicking a button after timeout

**Expected**: Error message "Approval request has expired or been removed"

### Test 5b: Bot Restart During Approval

1. Trigger approval
2. Restart the bot (while approval is pending)
3. Try clicking the button

**Expected**: Error message (pending approvals are not persisted)

## Verifying in Logs

If you have access to bot logs, you should see:

**When approval is requested:**
```
Agent requires approval for 1 tool(s)
Sent approval request 123456789 with 1 tool(s)
```

**When user approves:**
```
Tool approval 123456789 accepted by user
```

**When user rejects:**
```
Tool approval 123456789 rejected by user
```

**On timeout:**
```
Tool approval 123456789 timed out
```

## Common Issues

### Issue: Buttons Don't Appear

**Possible Causes:**
- Bot lacks permissions to send components
- Discord API issue
- Old Discord client version

**Solution:**
- Check bot permissions
- Try refreshing Discord
- Update Discord client

### Issue: Buttons Don't Respond

**Possible Causes:**
- Approval timed out
- Bot restarted (state lost)
- Network issue

**Solution:**
- Check logs
- Retry the command

### Issue: Bot Doesn't Recognize the Tool

**Possible Causes:**
- Typo in tool name
- Tool not registered properly

**Solution:**
- Use exact phrases like "test approval tool" or "test_discord_approval"
- Check that tool is imported and decorated correctly

## Automated Tests

Run the test suite:

```bash
# Run approval mechanism tests
pytest src/discord_approval_test.py -v

# Run integration tests
pytest src/tool_approval_integration_test.py -v

# Run all tests
pytest -v
```

## Next Steps

After confirming the basic mechanism works:

1. Add approval to specific production tools that need it
2. Consider implementing individual approval for multiple tools
3. Add role-based approval requirements
4. Implement approval history/audit log
5. Add custom approval messages per tool type

## Troubleshooting

If something doesn't work as expected:

1. Check bot logs for errors
2. Verify bot has necessary Discord permissions
3. Ensure PydanticAI version is compatible (1.0.15+)
4. Check that Discord.py version is compatible (2.6.4+)
5. Review docs/TOOL_APPROVAL.md for technical details
