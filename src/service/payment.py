from util import DatabaseSession, RedisSession
from typing import Tuple, Union
import stripe
import stripe.error
import os
from bson.objectid import ObjectId

stripe.api_key = os.getenv("STRIPE_API_KEY")


class PaymentService:
    db_session: DatabaseSession
    redis_session: RedisSession

    def __init__(self, db_session: DatabaseSession, redis_session: RedisSession):
        self.db_session = db_session
        self.redis_session = redis_session

    def get_intent(self, payment_id: str) -> str:
        intent = stripe.PaymentIntent.retrieve(payment_id)
        return intent.client_secret
    
    def get_payment_status(self, payment_id: str) -> Tuple[bool, Union[str, dict]]:
        success, data = self.db_session.findOne("payments", {"_id": ObjectId(payment_id)})
        if not success or len(data) == 0:
            return success, "Payment not Found"
        return success, data

    def webhook_handler(self, payload, sig_header, event) -> Tuple[bool, str]:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, os.getenv("STRIPE_ENDPOINT_SECRET")
            )
        except ValueError as e:
            return False, str(e)

        except stripe.error.SignatureVerificationError as e:
            return False, str(e)

        event_dict = event.to_dict()
        if event_dict['type'] == 'payment_intent.succeeded':
            payment_intent = event_dict['data']['object']
            success, err = self.db_session.insert("payments", {
                "user_id": payment_intent.metadata.user_id,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "status": payment_intent.status,
                "payment_intent_id": payment_intent.id
            })
            if not success:
                return False, err

            print(f"PaymentIntent was successful: {payment_intent.id}")
        elif event_dict['type'] == 'payment_intent.payment_failed':
            payment_intent = event_dict['data']['object']
            print(f"PaymentIntent failed: {payment_intent.id}")
            return False, "PaymentIntent failed"
        return True, "OK"
