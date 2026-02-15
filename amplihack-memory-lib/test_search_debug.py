import sys
sys.path.insert(0, 'src')

from pathlib import Path
import tempfile
from amplihack_memory.store import ExperienceStore
from amplihack_memory.experience import Experience, ExperienceType
from datetime import datetime

# Create temp storage
tmp = Path(tempfile.mkdtemp())
print(f"Using temp storage: {tmp}")

# Create store
store = ExperienceStore(agent_name="test-agent", storage_path=tmp)

# Add experience
exp = Experience(
    experience_type=ExperienceType.SUCCESS,
    context="Documentation quality check",
    outcome="Found 5 issues",
    confidence=0.9,
    timestamp=datetime.now()
)
exp_id = store.add(exp)
print(f"Added experience: {exp_id}")

# Check if it's in the database
conn = store.connector._connection
count = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
print(f"Experiences table has {count} rows")

fts_count = conn.execute("SELECT COUNT(*) FROM experiences_fts").fetchone()[0]
print(f"FTS table has {fts_count} rows")

# Try search
results = store.search("documentation")
print(f"Search found {len(results)} results")

if len(results) == 0:
    print("\nDEBUG: Checking what's in FTS table...")
    fts_rows = conn.execute("SELECT * FROM experiences_fts").fetchall()
    for row in fts_rows:
        print(f"  FTS row: {row}")
    
    print("\nDEBUG: Checking main table...")
    main_rows = conn.execute("SELECT experience_id, agent_name, context FROM experiences").fetchall()
    for row in main_rows:
        print(f"  Main row: {row}")
    
    print("\nDEBUG: Trying direct FTS query...")
    direct = conn.execute("SELECT * FROM experiences_fts WHERE experiences_fts MATCH 'documentation'").fetchall()
    print(f"Direct FTS query found {len(direct)} results")

