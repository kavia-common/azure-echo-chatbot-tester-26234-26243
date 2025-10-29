from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Import bot framework types lazily and keep import-time logic minimal to avoid URLConf load failures.
from botbuilder.schema import Activity
from .bot_adapter import get_adapter
from .bots import EchoBot


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
        - Validates content type is application/json.
        - Reads the Authorization header (if provided).
        - Deserializes request body into a Bot Framework Activity.
        - Invokes the BotFramework adapter to process the activity using EchoBot.

    Returns:
        HttpResponse:
            - 200 OK on success
            - 405 Method Not Allowed if not POST
            - 415 Unsupported Media Type when content-type is incorrect
            - 400 Bad Request for invalid/malformed JSON
            - 500 Internal Server Error for unhandled exceptions
    """
    if request.method != "POST":
        return HttpResponse(status=405)

    if request.content_type != "application/json":
        return HttpResponse(status=415)

    try:
        import json
        body = request.body.decode("utf-8")
        payload = json.loads(body) if body else {}
        activity = Activity().deserialize(payload)
    except Exception as e:
        # Invalid or malformed JSON
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
