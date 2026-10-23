import sqlite3, threading


class Buffer:
    """Stores alerts in SQLite when the broker is unreachable."""

    def __init__(self, path="edge/buffer.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.db.execute("CREATE TABLE IF NOT EXISTS q "
                            "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
                            "topic TEXT, payload TEXT)")
            self.db.commit()

    def save(self, topic, payload):
        with self.lock:
            self.db.execute("INSERT INTO q(topic, payload) VALUES (?, ?)",
                            (topic, payload))
            self.db.commit()

    def pending(self):
        with self.lock:
            return self.db.execute(
                "SELECT id, topic, payload FROM q ORDER BY id").fetchall()

    def delete(self, row_id):
        with self.lock:
            self.db.execute("DELETE FROM q WHERE id=?", (row_id,))
            self.db.commit()
