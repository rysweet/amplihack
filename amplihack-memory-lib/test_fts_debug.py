import sqlite3
from pathlib import Path
import tempfile

# Create test database
tmp = Path(tempfile.mkdtemp())
db_path = tmp / "test.db"

conn = sqlite3.connect(str(db_path))
conn.execute("PRAGMA journal_mode=WAL")

# Create schema
conn.execute("""
    CREATE TABLE experiences (
        experience_id TEXT PRIMARY KEY,
        agent_name TEXT,
        context TEXT,
        outcome TEXT
    )
""")

conn.execute("""
    CREATE VIRTUAL TABLE experiences_fts
    USING fts5(experience_id, context, outcome, content='experiences')
""")

conn.execute("""
    CREATE TRIGGER experiences_fts_insert AFTER INSERT ON experiences
    BEGIN
        INSERT INTO experiences_fts(experience_id, context, outcome)
        VALUES (new.experience_id, new.context, new.outcome);
    END
""")

# Insert test data
conn.execute("INSERT INTO experiences VALUES ('exp1', 'agent1', 'Documentation analysis', 'Good')")
conn.commit()

# Check if FTS was populated
fts_count = conn.execute("SELECT COUNT(*) FROM experiences_fts").fetchone()[0]
print(f"FTS table has {fts_count} rows")

# Try search
results = conn.execute("SELECT * FROM experiences_fts WHERE experiences_fts MATCH 'documentation'").fetchall()
print(f"Search for 'documentation' found {len(results)} results")

if results:
    print(f"Result: {results[0]}")
else:
    print("No results! Trying SELECT *...")
    all_fts = conn.execute("SELECT * FROM experiences_fts").fetchall()
    print(f"All FTS rows: {all_fts}")

conn.close()
