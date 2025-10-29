import logging
from typing import Optional

from django.conf import settings
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity

logger = logging.getLogger(__name__)


class AdapterWithErrorHandler(BotFrameworkAdapter):
    """
    PUBLIC_INTERFACE
    Adapter for the Bot Framework with a global error handler.
    This adapter reads credentials from Django settings.AZURE_BOT and logs any turn errors.
    """

    def __init__(self):
        cfg = getattr(settings, "AZURE_BOT", {})
        app_id = cfg.get("MICROSOFT_APP_ID") or None
        app_password = cfg.get("MICROSOFT_APP_PASSWORD") or None
        # Tenant optional; only used for single-tenant validation scenarios
        # Tenant ID is optional; not directly used by BotFrameworkAdapter settings in this SDK version.
        # Kept in config for future use or extended adapters.
        _ = cfg.get("MICROSOFT_APP_TENANT_ID") or None

        adapter_settings = BotFrameworkAdapterSettings(
            app_id=app_id,
            app_password=app_password,
            # Note: tenant_id is not a formal parameter in older SDKs.
            # Kept for potential future use or extended adapters.
        )
        super().__init__(adapter_settings)

        # Register a default error handler for the Adapter.
        async def on_error(context: TurnContext, error: Exception):
            logger.exception("Bot encountered an error: %s", error)

            # Send a trace activity, which will appear in the Bot Framework Emulator.
            await context.send_activity("The bot encountered an error or bug.")
            await context.send_activity("To continue to run this bot, please fix the bot source code.")

        self.on_turn_error = on_error

    # PUBLIC_INTERFACE
    async def process(self, auth_header: Optional[str], activity: Activity, logic):
        """
        PUBLIC_INTERFACE
        Process an incoming Activity using the adapter, given an auth_header and bot logic.

        :param auth_header: Authorization header from request (may be None for Emulator).
        :param activity: The activity object created from request JSON.
        :param logic: An async function that accepts a TurnContext.
        :return: Awaitable that completes after process_activity finishes.
        """
        # The SDK signature is process_activity(activity, auth_header, logic)
        return await self.process_activity(activity, auth_header, logic)


_adapter_singleton: Optional[AdapterWithErrorHandler] = None

# PUBLIC_INTERFACE
def get_adapter() -> AdapterWithErrorHandler:
    """
    PUBLIC_INTERFACE
    Returns a singleton instance of the AdapterWithErrorHandler to be reused across requests.
    """
    global _adapter_singleton
    if _adapter_singleton is None:
        _adapter_singleton = AdapterWithErrorHandler()
    return _adapter_singleton
