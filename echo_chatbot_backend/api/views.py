from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)

# Keep import-time logic minimal to avoid URLConf load failures.
# Defer any heavy imports (botbuilder, adapter creation) inside the view.
# Only import DRF/Django at module import time.

# PUBLIC_INTERFACE
@api_view(['GET'])
def health(request):
    """
    PUBLIC_INTERFACE
    Health check endpoint.

    Returns:
        Response: 200 OK with a JSON message indicating the server is up.
    """
    return Response({"message": "Server is up!"})


def _is_json_content_type(content_type: str | None) -> bool:
    """
    Check if the content type is JSON. Accept variants like 'application/json; charset=utf-8'.
    """
    if not content_type:
        return False
    return content_type.split(";")[0].strip().lower() == "application/json"


def _minimal_activity_validation(payload: dict) -> tuple[bool, str | None]:
    """
    Perform minimal validation for Bot Framework Activity needed by adapter.process_activity.
    We intentionally keep validation minimal and defer schema rules to the Bot Framework SDK.

    Required minimal keys for basic processing (relaxed):
    - type
    - channelId
    - serviceUrl
    - from
    - conversation

    Notes:
    - recipient is often populated by the channel/adapter and is not required for Emulator posts.
    - We only validate that nested 'from' and 'conversation' are objects if present.
    - We do NOT require 'id' anywhere; adapter/Bot can populate as needed.
    - serviceUrl can be any valid string, including localhost with random port as used by Emulator.

    Returns (ok, error_message).
    """
    required_fields = ["type", "channelId", "serviceUrl", "from", "conversation"]
    for f in required_fields:
        if f not in payload or payload[f] is None:
            return False, f"Missing required field: {f}"
    # Ensure nested dict-like structures exist where expected
    for nested in ["from", "conversation"]:
        if not isinstance(payload.get(nested), dict):
            return False, f"Field '{nested}' must be an object"
    # If recipient is present ensure it's an object, but do not require it
    if "recipient" in payload and not isinstance(payload.get("recipient"), dict):
        return False, "Field 'recipient' must be an object when provided"
    return True, None


# PUBLIC_INTERFACE
@csrf_exempt
def messages(request):
    """
    PUBLIC_INTERFACE
    Django view to handle Bot Framework activities at POST /api/messages.

    Usage:
        - POST JSON body representing a Bot Framework Activity.
        - Content-Type must be application/json.

    Behavior:
        - Validates content type is application/json (charset allowed).
        - Reads the Authorization header (if provided).
        - Deserializes request body into a Bot Framework Activity.
        - For Bot Framework Emulator (channelId='emulator'), skip JWT validation by clearing auth header.
        - Invokes the BotFramework adapter to process the activity using EchoBot.

    Returns:
        HttpResponse:
            - 200 OK on success
            - 405 Method Not Allowed if not POST
            - 415 Unsupported Media Type when content-type is incorrect
            - 400 Bad Request for invalid/malformed JSON
            - 400 Bad Request for missing required activity fields
            - 500 Internal Server Error for unhandled exceptions
    """
    if request.method != "POST":
        return HttpResponse(status=405)

    if not _is_json_content_type(request.META.get("CONTENT_TYPE")):
        error = {"error": {"reason": "unsupported_media_type", "message": "Unsupported Media Type. Use Content-Type: application/json."}}
        logger.warning("Messages 415: %s", error)
        return JsonResponse(error, status=415)

    # Lazy imports to prevent heavy operations at module import time
    try:
        import json
        from botbuilder.schema import Activity  # type: ignore
        from .bot_adapter import get_adapter
        from .bots import EchoBot
    except Exception as e:
        error = {"error": {"reason": "dependency_load_failure", "message": f"Failed to load bot dependencies: {str(e)}"}}
        logger.exception("Messages 500 during dependency load: %s", e)
        return JsonResponse(error, status=500)

    # Parse JSON body
    try:
        # Prefer raw body to avoid DRF parsing side-effects and to control error messages
        raw = request.body.decode("utf-8") if request.body is not None else ""
        if not raw:
            error = {"error": {"reason": "empty_body", "message": "Empty request body."}}
            logger.warning("Messages 400: %s", error)
            return JsonResponse(error, status=400)
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            error = {"error": {"reason": "invalid_type", "message": "JSON payload must be an object."}}
            logger.warning("Messages 400: %s", error)
            return JsonResponse(error, status=400)
    except Exception as e:
        error = {"error": {"reason": "invalid_json", "message": f"Invalid JSON payload: {str(e)}"}}
        logger.warning("Messages 400 invalid JSON: %s", e)
        return JsonResponse(error, status=400)

    # Minimal validation for required fields (relaxed for Emulator-style payloads)
    ok, err = _minimal_activity_validation(payload)
    if not ok:
        error = {"error": {"reason": "invalid_activity", "message": err}}
        logger.warning("Messages 400 invalid activity: %s; payload keys=%s", err, list(payload.keys()))
        return JsonResponse(error, status=400)

    # Deserialize to Activity
    try:
        activity = Activity().deserialize(payload)
    except Exception as e:
        # Do not strictly enforce schema here; return helpful error.
        error = {"error": {"reason": "schema_deserialize_error", "message": f"Invalid Activity schema: {str(e)}"}}
        logger.warning("Messages 400 schema deserialize error: %s", e)
        return JsonResponse(error, status=400)

    # Emulator handling:
    # For Bot Framework Emulator, bypass JWT validation entirely regardless of any Authorization header it might send.
    # Emulator traffic uses channelId='emulator'. We explicitly null auth_header so adapter skips JWT checks.
    incoming_auth = request.headers.get("Authorization")
    auth_header = incoming_auth
    if payload.get("channelId") == "emulator":
        auth_header = None

    adapter = get_adapter()
    bot = EchoBot()

    async def aux_logic(turn_context):
        await bot.on_turn(turn_context)

    try:
        # Use adapter to process the incoming activity
        task = adapter.process(auth_header, activity, aux_logic)

        # Ensure completion in sync view
        import asyncio
        if asyncio.iscoroutine(task):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Running inside an event loop; create a new one for blocking wait
                    new_loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(new_loop)
                        new_loop.run_until_complete(task)
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(loop)
                else:
                    loop.run_until_complete(task)
            except RuntimeError:
                # No current loop; create one
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(task)
                finally:
                    loop.close()
    except Exception as e:
        # Unexpected error within adapter/bot logic
        logger.exception("Messages 500 during adapter/bot processing: %s", e)
        return JsonResponse({"error": {"reason": "adapter_error", "message": str(e)}}, status=500)

    # As per Bot Framework protocol, respond 200 with no body for successful processing
    return HttpResponse(status=200)
