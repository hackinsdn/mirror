"""MongoController."""

# pylint: disable=unnecessary-lambda,invalid-name
import os
from datetime import datetime
from typing import Dict, Optional

from pymongo.collection import ReturnDocument
from pymongo.errors import AutoReconnect
from tenacity import retry_if_exception_type, stop_after_attempt, wait_random

from kytos.core.db import Mongo
from kytos.core.retry import before_sleep, for_all_methods, retries


@for_all_methods(
    retries,
    stop=stop_after_attempt(
        int(os.environ.get("MONGO_AUTO_RETRY_STOP_AFTER_ATTEMPT", "3"))
    ),
    wait=wait_random(
        min=int(os.environ.get("MONGO_AUTO_RETRY_WAIT_RANDOM_MIN", "1")),
        max=int(os.environ.get("MONGO_AUTO_RETRY_WAIT_RANDOM_MAX", "1")),
    ),
    before_sleep=before_sleep,
    retry=retry_if_exception_type((AutoReconnect,)),
)
class MongoController:
    """Mongo Controller"""

    def __init__(self, get_mongo=lambda: Mongo()) -> None:
        self.mongo = get_mongo()
        self.db_client = self.mongo.client
        self.db = self.db_client[self.mongo.db_name]

    def get_mirror(self, mirror_id: str) -> Dict:
        """Get mirror by id."""
        return self.db.mirrors.find_one({"_id": mirror_id}) or {}

    def get_mirrors(self, filters: Dict = {}) -> Dict:
        """Get all mirrors."""
        return self.db.mirrors.find(projection={'_id': False})

    def upsert_mirror(self, mirror_id: str, mirror: Dict) -> Optional[Dict]:
        """Update or insert an EVC"""
        utc_now = datetime.utcnow()
        updated = self.db.mirrors.find_one_and_update(
            {"_id": mirror_id},
            {
                "$set": mirror | {"updated_at": utc_now},
                "$setOnInsert": {"inserted_at": utc_now},
            },
            return_document=ReturnDocument.AFTER,
            upsert=True,
        )
        return updated
