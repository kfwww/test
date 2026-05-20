from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from infrastructure.utils import utc_now, generate_uuid


@dataclass
class User:
    id: UUID = field(default_factory=generate_uuid)
    created_at: datetime = field(default_factory=utc_now)