# Echo Chatbot Backend (Django + Azure Bot Framework)

This backend exposes:
- GET /api/health/ — Simple health check.
- POST /api/messages — Azure Bot Framework activities endpoint with an echo bot.

The bot is built using Microsoft Bot Framework SDK for Python and is configured via environment variables.

## Environment Variables

Provide the following environment variables (optional for local Emulator testing without credentials):

- MICROSOFT_APP_ID: Your Microsoft App Registration (Application/Client) ID.
- MICROSOFT_APP_PASSWORD: The client secret for the above app registration.
- MICROSOFT_APP_TENANT_ID: Optional. Directory (tenant) ID for single-tenant bots.
- BOT_OPEN_ID_VALIDATION: Optional. "true"/"false" to toggle strict OpenID validation; default is false.

These are loaded into Django settings under `settings.AZURE_BOT`.

Note: Do not commit secrets. Ask the operator to set these in the .env for deployment.

## Endpoints

- Health: GET {BASE_URL}/api/health/
- Bot Messages: POST {BASE_URL}/api/messages

Content-Type must be `application/json` for the messages endpoint.

## Running locally

Install dependencies (ensure you are in the `echo_chatbot_backend` folder):

- Python deps are listed in `requirements.txt` (includes `botbuilder-core` and `botbuilder-schema`).

Run checks and start Django as you normally would, then:

- Verify URLConf loads and dependencies using:
  python manage.py check

- Validate the health endpoint:
  curl -i {BASE_URL}/api/health/

- Test the messages endpoint with a sample echo activity:
  curl -i -X POST "{BASE_URL}/api/messages" \
    -H "Content-Type: application/json" \
    -d '{
      "type": "message",
      "text": "hello",
      "from": {"id": "user1"},
      "recipient": {"id": "bot1"},
      "conversation": {"id": "conv1"},
      "channelId": "emulator",
      "serviceUrl": "http://localhost"
    }'

You should receive HTTP 200.

## Using Bot Framework Emulator (no credentials)

- Leave MICROSOFT_APP_ID and MICROSOFT_APP_PASSWORD empty.
- Start Bot Framework Emulator.
- Set the Bot URL to: {BASE_URL}/api/messages
- Choose "No authentication" for a quick local test.
- Send a message; the bot will echo it back.

## Deploying with Azure Bot Resource (with credentials)

1. Create or use an existing App Registration and generate a client secret.
2. Create an Azure Bot resource and configure the Messaging endpoint to:
   {PUBLIC_BASE_URL}/api/messages
3. Set the environment variables:
   - MICROSOFT_APP_ID
   - MICROSOFT_APP_PASSWORD
   - MICROSOFT_APP_TENANT_ID (optional)
4. Restart the app so settings take effect.

## Notes

- The adapter uses a global error handler and logs exceptions.
- The messages endpoint requires `application/json` content type.
- The health endpoint remains unchanged for simple monitoring.

``` 

