import platform
from typing import Optional


APP_ID = "CodexLens"


def notify(title: str, message: str, app_id: str = APP_ID) -> bool:
    """Best-effort desktop notification.

    Windows uses winotify when installed. Notification failures are ignored so
    install/startup flows never fail only because notifications are unavailable.
    """
    if platform.system() != "Windows":
        return False

    try:
        from winotify import Notification
    except Exception:
        return False

    try:
        toast = Notification(app_id=app_id, title=title, msg=message)
        toast.show()
        return True
    except Exception:
        return False
