"""
Push notification dispatch via Firebase Cloud Messaging.

This is intentionally decoupled from the alert-detection logic
(check_alerts.py): detection always runs and always writes Alert rows,
whether or not Firebase is configured. Push is a best-effort add-on —
if firebase-admin isn't installed or FIREBASE_CREDENTIALS_PATH isn't
set, we log and skip rather than fail the whole job.

Setup (you'll need your own Firebase project — none of this works with
placeholder credentials):
  1. Create a Firebase project, add Android/iOS apps to it.
  2. Project Settings -> Service Accounts -> Generate new private key,
     save the JSON somewhere the backend can read.
  3. pip install firebase-admin
  4. Set FIREBASE_CREDENTIALS_PATH in your environment to that JSON's path.
"""
import logging
from decouple import config

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    cred_path = config("FIREBASE_CREDENTIALS_PATH", default=None)
    if not cred_path:
        logger.info("FIREBASE_CREDENTIALS_PATH not set — push notifications disabled.")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.warning("firebase-admin not installed — push notifications disabled. `pip install firebase-admin`.")
        return None

    try:
        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        return _firebase_app
    except Exception as e:
        logger.error(f"Could not initialize Firebase: {e}")
        return None


def send_push_to_users(users, title, body, data=None):
    """
    `users` is an iterable of User instances. Sends to every registered
    device token for each. Silently does nothing if push isn't configured.
    Returns the number of tokens successfully sent to.
    """
    app = _get_firebase_app()
    if app is None:
        return 0

    from firebase_admin import messaging

    tokens = []
    for user in users:
        tokens.extend(user.device_tokens.values_list("token", flat=True))
    tokens = list(set(tokens))
    if not tokens:
        return 0

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=tokens,
    )
    try:
        response = messaging.send_each_for_multicast(message)
        return response.success_count
    except Exception as e:
        logger.error(f"FCM send failed: {e}")
        return 0
