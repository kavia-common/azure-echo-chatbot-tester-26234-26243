from typing import List

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount


class EchoBot(ActivityHandler):
    """
    PUBLIC_INTERFACE
    A simple echo bot that greets new members and echoes back message text.
    """

    async def on_members_added_activity(self, members_added: List[ChannelAccount], turn_context: TurnContext):
        """
        Greet members who are added to the conversation.
        """
        for member in members_added:
            # Greet others (not the bot itself)
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome! Send me a message and I'll echo it back.")

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Echo the incoming user message text.
        """
        text = turn_context.activity.text or ""
        if text.strip():
            await turn_context.send_activity(f"You said: {text}")
        else:
            await turn_context.send_activity("I didn't catch any text. Try sending some words!")
