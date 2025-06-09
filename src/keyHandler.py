import yaml
import sqlite3
from datetime import datetime

def openConn(db_path):
    global cursor, conn

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

def closeConn():
    conn.close()

def initDB():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apiKeys (
        id TEXT PRIMARY KEY,
        project_name TEXT,
        project_number INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keyLogs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_id TEXT SECONDARY NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        success BOOLEAN NOT NULL,
        error TEXT
    )
    """)

    conn.commit()

def loadKeysData(yaml_file_path):
    with open(yaml_file_path, "r") as file:
        api_keys_data = yaml.safe_load(file)

    # delete removed keys
    yaml_keys = {api["key_id"] for api in api_keys_data}

    cursor.execute("SELECT id FROM apiKeys")
    db_keys = {row[0] for row in cursor.fetchall()}

    keys_to_delete = db_keys - yaml_keys

    for key in keys_to_delete:
        cursor.execute("DELETE FROM apiKeys WHERE id = ?", (key,))

    # update/insert keys
    for api in api_keys_data:
        cursor.execute("""
            INSERT INTO apiKeys (id, project_name, project_number)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                project_name=excluded.project_name,
                project_number=excluded.project_number
        """, (api["key_id"], api["project_name"], api["project_number"]))
    
    conn.commit()

def addSampleLogData():
    cursor.executemany("""
        INSERT INTO keyLogs (key_id, timestamp, success, error)
        VALUES (?, ?, ?, ?)
    """, [
        ("API_KEY1", datetime(2020, 5, 14), True, None),
        ("API_KEY1", datetime(2020, 5, 15), True, None),
        ("API_KEY1", datetime(2020, 5, 16), True, None),
        ("API_KEY1", datetime(2020, 5, 17), False, "1007"),
        ("API_KEY2", datetime(2020, 5, 18), True, None),
        ("API_KEY2", datetime(2020, 5, 19), True, None),
        ("API_KEY2", datetime(2020, 5, 20), False, "1007"),
    ])

    conn.commit()

def getKeyId():
    # get last used key
    cursor.execute("""
        SELECT key_id, success
        FROM keyLogs
        ORDER BY timestamp DESC
        LIMIT 1
    """)

    key_id, success = cursor.fetchone()
    if (success):
        return key_id
    else:
        return getNextKeyId(key_id)
    
def getNextKeyId(currKeyId):
    keyCount = getKeyCount()
    return currKeyId[:-1] + str((int(currKeyId[7:]) + 1) % keyCount)

def getKeyCount():
    cursor.execute("SELECT COUNT(*) FROM apiKeys")
    return cursor.fetchone()[0]

def insertKeyLog(key_id, success, error):
    cursor.execute("""
        INSERT INTO keyLogs (key_id, success, error)
        VALUES (?, ?, ?)
    """, (key_id, success, error))
    conn.commit()
    print("key log inserted")