
from app.database.queries import save_wallet_event


def test_save_wallet_event():
    result = {
        "signature": "TEST_SIGNATURE_DELETE_ME",
        "type": "TRANSFER",
        "translated_type": "receive_native_token",
        "time": 1792300000,
        "from_user_address": "TEST_SENDER",
        "to_user_address": "TEST_RECEIVER",
        "direction": "in",
        "amount": 0.5,
        "mint": "So11111111111111111111111111111111111111112",
    }

    save_wallet_event(
        wallet_address="TEST_WALLET_DELETE_ME",
        result=result,
    )

    print("Event saved successfully!")


if __name__ == "__main__":
    test_save_wallet_event()
