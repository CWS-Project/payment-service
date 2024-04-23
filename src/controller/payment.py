from fastapi import APIRouter, Response, Request
from dtypes import make_response
from service import PaymentService
from util import DatabaseSession, RedisSession
import json

payment_service = PaymentService(
    db_session=DatabaseSession(),
    redis_session=RedisSession()
)

router = APIRouter(prefix="/api/v1/payments", tags=["Payment"])


@router.post("/webhook")
async def webhook_route(request: Request, response: Response):
    payload = await request.body()
    event = None

    try:
        event = json.loads(payload)
    except json.decoder.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return make_response(response, 500, "Error decoding JSON", None)

    sig_header = request.headers.get("stripe-signature")
    success, message = payment_service.webhook_handler(payload, sig_header, event)
    if not success:
        print(f"Error handling webhook: {message}")
        return make_response(response, 500, message, None)
    
    return make_response(response, 200, message, None)


@router.get("/intent/{payment_id}")
async def get_payment_intent(payment_id: str, response: Response):
    client_secret = payment_service.get_intent(payment_id)
    return make_response(response, 200, "Payment Intent retrieved", {"client_secret": client_secret})


@router.get("/status/{payment_id}")
async def get_payment_status(payment_id: str, response: Response):
    success, data = payment_service.get_payment_status(payment_id)
    if not success:
        return make_response(response, 500, data, None)
    return make_response(response, 200, "Payment Status retrieved", data)
