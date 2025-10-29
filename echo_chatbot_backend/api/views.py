from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from botbuilder.schema import Activity
from .bot_adapter import get_adapter
from .bots import EchoBot


@api_view(['GET'])
def health(request):
    """
    PUBLIC_INTERFACE
    Health check endpoint.

    Returns:
        200 OK with a JSON message indicating the server is up.
    """
    return Response({"message": "Server is up!"})


# PUBLIC_INTERFACE
@csrf_exempt
def messages(request):
    """
    PUBLIC_INTERFACE
    Django view to handle Bot Framework activities at POST /api/messages.

    - Validates content type is application/json.
    - Reads the Authorization header (if provided).
    - Deserializes request body into a Bot Framework Activity.
    - Invokes the BotFramework adapter to process the activity using EchoBot.
    - Returns:
        200 OK on success
        415 Unsupported Media Type when content-type is incorrect
        500 with JSON details on unhandled exceptions
    """
    if request.method != "POST":
        return HttpResponse(status=405)

    if request.content_type != "application/json":
        return HttpResponse(status=415)

    try:
        body = request.body.decode("utf-8")
        activity = Activity().deserialize(request.json if hasattr(request, "json") else None)
    except Exception:
        # Some Django setups don't attach parsed json; parse from body directly.
        import json
        try:
            payload = json.loads(body) if body else {}
            activity = Activity().deserialize(payload)
        except Exception as e:
            return JsonResponse({"error": f"Invalid JSON payload: {str(e)}"}, status=400)

    auth_header = request.headers.get("Authorization", None)

    adapter = get_adapter()
    bot = EchoBot()

    async def aux_logic(turn_context):
        await bot.on_turn(turn_context)

    try:
        # Use adapter to process the incoming activity
        task = adapter.process(auth_header, activity, aux_logic)
        # If running under sync view, ensure completion
        # Botbuilder returns an awaitable; we must run it to completion.
        import asyncio
        if asyncio.iscoroutine(task):
            asyncio.get_event_loop().run_until_complete(task)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return HttpResponse(status=200)
