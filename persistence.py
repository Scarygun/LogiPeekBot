import pickle
import logging
from typing import Any, Dict, Optional, Tuple, cast
from telegram.ext import BasePersistence, PersistenceInput
from database import get_db

logger = logging.getLogger(__name__)

class MongoPersistence(BasePersistence):
    """A persistence class that uses MongoDB to store data."""

    def __init__(self):
        super().__init__()
        self.db = get_db()
        self.conversations_collection = self.db.persistence_conversations
        self.user_data_collection = self.db.persistence_user_data
        self.chat_data_collection = self.db.persistence_chat_data
        self.bot_data_collection = self.db.persistence_bot_data
        self.callback_data_collection = self.db.persistence_callback_data

    async def get_user_data(self) -> Dict[int, Any]:
        """Loads user data from MongoDB."""
        data = {}
        for doc in self.user_data_collection.find():
            user_id = doc["user_id"]
            data[user_id] = pickle.loads(doc["data"])
        return data

    async def update_user_data(self, user_id: int, user_data: Any) -> None:
        """Saves user data into MongoDB."""
        if not user_data:
            self.user_data_collection.delete_one({"user_id": user_id})
            return
        self.user_data_collection.replace_one(
            {"user_id": user_id},
            {"user_id": user_id, "data": pickle.dumps(user_data)},
            upsert=True
        )

    async def get_chat_data(self) -> Dict[int, Any]:
        """Loads chat data from MongoDB."""
        data = {}
        for doc in self.chat_data_collection.find():
            chat_id = doc["chat_id"]
            data[chat_id] = pickle.loads(doc["data"])
        return data

    async def update_chat_data(self, chat_id: int, chat_data: Any) -> None:
        """Saves chat data into MongoDB."""
        if not chat_data:
            self.chat_data_collection.delete_one({"chat_id": chat_id})
            return
        self.chat_data_collection.replace_one(
            {"chat_id": chat_id},
            {"chat_id": chat_id, "data": pickle.dumps(chat_data)},
            upsert=True
        )

    async def get_bot_data(self) -> Dict[Any, Any]:
        """Loads bot data from MongoDB."""
        doc = self.bot_data_collection.find_one({"_id": "bot_data"})
        if doc:
            return pickle.loads(doc["data"])
        return {}

    async def update_bot_data(self, bot_data: Any) -> None:
        """Saves bot data into MongoDB."""
        self.bot_data_collection.replace_one(
            {"_id": "bot_data"},
            {"data": pickle.dumps(bot_data)},
            upsert=True
        )

    async def get_conversations(self, name: str) -> Dict[Tuple[Any, ...], Any]:
        """Loads conversations from MongoDB."""
        doc = self.conversations_collection.find_one({"name": name})
        if doc:
            # MongoDB doesn't support tuples as keys, so we store as string and reconstruct
            raw_data = pickle.loads(doc["data"])
            return raw_data
        return {}

    async def update_conversation(self, name: str, key: Tuple[Any, ...], new_state: Optional[Any]) -> None:
        """Saves conversation state into MongoDB."""
        # This is called for every state update in a ConversationHandler
        # Because we need the whole dict for get_conversations, we update a sub-document
        # or load the whole thing, update and save.
        
        doc = self.conversations_collection.find_one({"name": name})
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

    async def get_callback_data(self) -> Optional[Tuple[Any, Any]]:
        """Loads callback data from MongoDB."""
        doc = self.callback_data_collection.find_one({"_id": "callback_data"})
        if doc:
            return pickle.loads(doc["data"])
        return None

    async def update_callback_data(self, data: Tuple[Any, Any]) -> None:
        """Saves callback data into MongoDB."""
        self.callback_data_collection.replace_one(
            {"_id": "callback_data"},
            {"data": pickle.dumps(data)},
            upsert=True
        )

    async def flush(self) -> None:
        """Does nothing in our case as we update on every call."""
        pass

    async def drop_chat_data(self, chat_id: int) -> None:
        """Removes chat data from MongoDB."""
        self.chat_data_collection.delete_one({"chat_id": chat_id})

    async def drop_user_data(self, user_id: int) -> None:
        """Removes user data from MongoDB."""
        self.user_data_collection.delete_one({"user_id": user_id})

    async def refresh_bot_data(self, bot_data: Any) -> Any:
        """Refreshes bot data from MongoDB."""
        db_data = await self.get_bot_data()
        return db_data if db_data else bot_data

    async def refresh_chat_data(self, chat_id: int, chat_data: Any) -> Any:
        """Refreshes chat data from MongoDB."""
        doc = self.chat_data_collection.find_one({"chat_id": chat_id})
        if doc:
            return pickle.loads(doc["data"])
        return chat_data

    async def refresh_user_data(self, user_id: int, user_data: Any) -> Any:
        """Refreshes user data from MongoDB."""
        doc = self.user_data_collection.find_one({"user_id": user_id})
        if doc:
            return pickle.loads(doc["data"])
        return user_data
