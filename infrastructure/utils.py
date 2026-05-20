from datetime import datetime, timezone
from uuid import UUID, uuid4


def generate_uuid() -> UUID:
    return uuid4()

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)