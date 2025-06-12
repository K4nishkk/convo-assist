import yaml
from datetime import datetime
import aiosqlite
import asyncio
import logging
from collections import deque

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)

class KeyManager:
    def __init__(self, db_path, yaml_file_path) -> None:
        self.db_path = db_path
        self.yaml_file_path = yaml_file_path

    async def _openConn(self):
        self.db = await aiosqlite.connect(self.db_path)

    async def _closeConn(self):
        await self.db.close()

    async def _initDB(self):
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS apiKeys (
                id TEXT PRIMARY KEY,
                project_name TEXT,
                project_number INTEGER
            )
        """)

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS keyLogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT SECONDARY NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN NOT NULL,
                error TEXT,
                lag FLOAT,
                total_bytes INTEGER,
                audio_duration FLOAT
            )
        """)

        await self.db.commit()

    # updating apikeys table and storing key count
    async def _updateApiKeysInDB(self):
        with open(self.yaml_file_path, "r") as file:
            api_keys_data = yaml.safe_load(file)

        # delete removed keys
        yaml_keys = {api["key_id"] for api in api_keys_data}

        cursor = await self.db.execute("SELECT id FROM apiKeys")
        rows = await cursor.fetchall()
        db_keys = {row[0] for row in rows}

        keys_to_delete = db_keys - yaml_keys

        for key in keys_to_delete:
            await self.db.execute("DELETE FROM apiKeys WHERE id = ?", (key,))

        # update/insert keys
        for api in api_keys_data:
            await self.db.execute("""
                INSERT INTO apiKeys (id, project_name, project_number)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    project_name=excluded.project_name,
                    project_number=excluded.project_number
            """, (api["key_id"], api["project_name"], api["project_number"]))
        
        await self.db.commit()

        # getting key count
        cursor = await self.db.execute("SELECT COUNT(*) FROM apiKeys")
        row = await cursor.fetchone()
        self.keyCount = row[0] if row else 0

    # create list in priority order
    async def _createKeysList(self):
        cursor = await self.db.execute("SELECT id FROM apiKeys")
        rows = await cursor.fetchall()
        self.keysList = [row[0] for row in rows]
        self.iterator = None

    async def init(self):
        await self._openConn()
        await self._initDB()
        await self._updateApiKeysInDB()
        await self._createKeysList()
        await self._closeConn()

    async def insertKeyLog(self, key_id, success=True, error=None, lag=None, total_bytes=None, audio_duration=None):
        await self._openConn()
        await self.db.execute(
            """
            INSERT INTO keyLogs (key_id, success, error, lag, total_bytes, audio_duration)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (key_id, success, error, lag, total_bytes, audio_duration)
        )

        await self.db.commit()
        await self._closeConn()
        logging.info(f"Key log inserted: KEY_ID={key_id} SUCCESS={success}")

    def getKeyId(self):
        if not self.iterator:
            self.iterator = 0

        key_id = self.keysList[self.iterator]
        self.iterator = (self.iterator + 1) % self.keyCount
        logging.info(f"Using KEY_ID: {key_id}")
        return key_id

async def main():
    db = KeyManager("api_keys.sqlite", "api-keys.yaml")
    await db.init()
    print(f"keyCount: {db.keyCount}")
    print(f"keysList: {db.keysList}")
    print(db.getKeyId())
    print(db.getKeyId())
    await db.insertKeyLog(key_id="API_KEY0", success=True, lag=1.55, total_bytes=10000, audio_duration=4.55)
    await db.insertKeyLog(key_id="API_KEY0", success=True, lag=2.55, total_bytes=20000, audio_duration=5.55)
    await db.insertKeyLog(key_id="API_KEY0", success=True, lag=3.55, total_bytes=30000, audio_duration=6.55)
    await db.insertKeyLog(key_id="API_KEY0", success=False, error=1007)
    await db.insertKeyLog(key_id="API_KEY1", success=True, lag=1.55, total_bytes=10000, audio_duration=4.55)
    await db.insertKeyLog(key_id="API_KEY1", success=True, lag=2.55, total_bytes=20000, audio_duration=5.55)

if __name__ == "__main__":
    asyncio.run(main())