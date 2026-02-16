"""Discord UI components for tool approval mechanism."""

import asyncio
import discord
from discord.ui import View, Button
from loguru import logger
from typing import Dict, Tuple
from pydantic_ai import DeferredToolRequests, DeferredToolResults


# Global storage for pending approvals
# Maps: message_id -> (DeferredToolRequests, asyncio.Future)
pending_approvals: Dict[int, Tuple[DeferredToolRequests, asyncio.Future]] = {}


class ApprovalView(View):
    """Discord View with Accept/Reject buttons for tool approval."""

    def __init__(self, message_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.message_id = message_id
        self.result: DeferredToolResults | None = None

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handle accept button click."""
        await interaction.response.defer()

        # Get the pending approval data
        if self.message_id not in pending_approvals:
            await interaction.followup.send(
                "Error: Approval request has expired or been removed.", ephemeral=True
            )
            return

        deferred_requests, future = pending_approvals[self.message_id]

        # Build approval results - approve all requests
        results = DeferredToolResults()
        for call in deferred_requests.approvals:
            results.approvals[call.tool_call_id] = True

        # Update the message to show it was accepted
        await interaction.message.edit(
            content=interaction.message.content + "\n\n**✅ APPROVED by user**",
            view=None,
        )

        # Set the future result to continue agent execution
        future.set_result(results)

        # Clean up
        del pending_approvals[self.message_id]

        logger.info(f"Tool approval {self.message_id} accepted by user")

    @discord.ui.button(label="❌ Reject", style=discord.ButtonStyle.danger)
    async def reject_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handle reject button click."""
        await interaction.response.defer()

        # Get the pending approval data
        if self.message_id not in pending_approvals:
            await interaction.followup.send(
                "Error: Approval request has expired or been removed.", ephemeral=True
            )
            return

        deferred_requests, future = pending_approvals[self.message_id]

        # Build approval results - reject all requests
        from pydantic_ai import ToolDenied

        results = DeferredToolResults()
        for call in deferred_requests.approvals:
            results.approvals[call.tool_call_id] = ToolDenied(
                "User rejected the tool call"
            )

        # Update the message to show it was rejected
        await interaction.message.edit(
            content=interaction.message.content + "\n\n**❌ REJECTED by user**",
            view=None,
        )

        # Set the future result to continue agent execution
        future.set_result(results)

        # Clean up
        del pending_approvals[self.message_id]

        logger.info(f"Tool approval {self.message_id} rejected by user")


async def request_approval(
    thread: discord.Thread, deferred_requests: DeferredToolRequests
) -> DeferredToolResults:
    """
    Request user approval for deferred tool calls via Discord UI.

    Args:
        thread: Discord thread to send the approval request to
        deferred_requests: The deferred tool requests from the agent

    Returns:
        DeferredToolResults with user's approval/rejection decisions
    """
    # Format the approval request message
    message_parts = ["🔔 **Tool Approval Required**\n"]
    message_parts.append("The following tools require your confirmation:\n")

    for call in deferred_requests.approvals:
        message_parts.append(f"\n**Tool:** `{call.tool_name}`")
        message_parts.append(f"**Parameters:**")

        # Format the arguments nicely
        for key, value in call.args.items():
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            message_parts.append(f"  • {key}: `{value_str}`")

        # Include metadata if available
        if (
            deferred_requests.metadata
            and call.tool_call_id in deferred_requests.metadata
        ):
            metadata = deferred_requests.metadata[call.tool_call_id]
            message_parts.append(f"**Metadata:** {metadata}")

    message_parts.append("\n**Please approve or reject this action:**")
    message_content = "\n".join(message_parts)

    # Send the approval request with buttons
    view = ApprovalView(message_id=0)  # Temporary ID
    approval_message = await thread.send(message_content, view=view)

    # Create a future to wait for user response
    future = asyncio.Future()

    # Store the pending approval with the actual message ID
    view.message_id = approval_message.id
    pending_approvals[approval_message.id] = (deferred_requests, future)

    logger.info(
        f"Sent approval request {approval_message.id} with {len(deferred_requests.approvals)} tool(s)"
    )

    # Wait for user response (with timeout handled by View)
    try:
        result = await asyncio.wait_for(future, timeout=300)  # 5 minutes
        return result
    except asyncio.TimeoutError:
        # Clean up on timeout
        if approval_message.id in pending_approvals:
            del pending_approvals[approval_message.id]

        # Update the message to show timeout
        await approval_message.edit(
            content=message_content + "\n\n**⏱️ TIMEOUT - Request expired**", view=None
        )

        logger.warning(f"Tool approval {approval_message.id} timed out")

        # Return rejection for all tools on timeout
        from pydantic_ai import ToolDenied

        results = DeferredToolResults()
        for call in deferred_requests.approvals:
            results.approvals[call.tool_call_id] = ToolDenied(
                "Approval request timed out"
            )
        return results
