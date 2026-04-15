import asyncio
import pickle
import logging
from typing import Any, Dict, Optional, Tuple, cast
from telegram.ext import BasePersistence, PersistenceInput
from database import get_db

logger = logging.getLogger(__name__)

class MongoPersistence(BasePersistence):
    """A persistence class that uses MongoDB to store data."""

    def __init__(self):
        super().__init__(
            store_data=PersistenceInput(
                user_data=True,
                chat_data=False,
                bot_data=False,
                callback_data=False,
            )
        )
        self.db = get_db()
        self.conversations_collection = self.db.persistence_conversations
        self.user_data_collection = self.db.persistence_user_data

    async def get_user_data(self) -> Dict[int, Any]:
        """Loads user data from MongoDB."""
        def _load() -> Dict[int, Any]:
            data = {}
            for doc in self.user_data_collection.find({}, {"user_id": 1, "data": 1}):
                user_id = doc["user_id"]
                data[user_id] = pickle.loads(doc["data"])
            return data

        return await asyncio.to_thread(_load)

    async def update_user_data(self, user_id: int, user_data: Any) -> None:
        """Saves user data into MongoDB."""
        def _update() -> None:
            if not user_data:
                self.user_data_collection.delete_one({"user_id": user_id})
                return
            self.user_data_collection.replace_one(
                {"user_id": user_id},
                {"user_id": user_id, "data": pickle.dumps(user_data)},
                upsert=True
            )

        await asyncio.to_thread(_update)

    async def get_chat_data(self) -> Dict[int, Any]:
        """Chat data persistence is disabled to keep webhook startup lean."""
        return {}

    async def update_chat_data(self, chat_id: int, chat_data: Any) -> None:
        """Chat data persistence is disabled to keep webhook startup lean."""
        return None

    async def get_bot_data(self) -> Dict[Any, Any]:
        return {}

    async def update_bot_data(self, bot_data: Any) -> None:
        return None

    async def get_conversations(self, name: str) -> Dict[Tuple[Any, ...], Any]:
        """Loads conversations from MongoDB."""
        def _load() -> Dict[Tuple[Any, ...], Any]:
            doc = self.conversations_collection.find_one({"name": name}, {"data": 1})
            if doc:
                return pickle.loads(doc["data"])
            return {}

        return await asyncio.to_thread(_load)

    async def update_conversation(self, name: str, key: Tuple[Any, ...], new_state: Optional[Any]) -> None:
        """Saves conversation state into MongoDB."""
        def _update() -> None:
            doc = self.conversations_collection.find_one({"name": name}, {"data": 1})
            data = pickle.loads(doc["data"]) if doc else {}

            if new_state is not None:
                data[key] = new_state
            else:
                data.pop(key, None)

            self.conversations_collection.replace_one(
                {"name": name},
                {"name": name, "data": pickle.dumps(data)},
                upsert=True
            )

        await asyncio.to_thread(_update)

    async def get_callback_data(self) -> Optional[Tuple[Any, Any]]:
        return None

    async def update_callback_data(self, data: Tuple[Any, Any]) -> None:
        return None

    async def flush(self) -> None:
        """Does nothing in our case as we update on every call."""
        pass

    async def drop_chat_data(self, chat_id: int) -> None:
        return None

    async def drop_user_data(self, user_id: int) -> None:
        """Removes user data from MongoDB."""
        await asyncio.to_thread(self.user_data_collection.delete_one, {"user_id": user_id})

    async def refresh_bot_data(self, bot_data: Any) -> Any:
        return bot_data

    async def refresh_chat_data(self, chat_id: int, chat_data: Any) -> Any:
        return chat_data

    async def refresh_user_data(self, user_id: int, user_data: Any) -> Any:
        """Refreshes user data from MongoDB."""
        def _load() -> Any:
            doc = self.user_data_collection.find_one({"user_id": user_id}, {"data": 1})
            if doc:
                return pickle.loads(doc["data"])
            return user_data

        return await asyncio.to_thread(_load)
