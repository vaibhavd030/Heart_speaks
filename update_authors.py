import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "messages.db")

def update_authors():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT source_file, full_text FROM messages")
    rows = cursor.fetchall()
    
    for source_file, full_text in rows:
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        if lines:
            author = lines[-1]
            # Some cleaning just in case
            if len(author) > 50:
                author = "Spiritual Guide"
            cursor.execute("UPDATE messages SET author = ? WHERE source_file = ?", (author, source_file))
            
    conn.commit()
    conn.close()
    print(f"Updated authors for {len(rows)} messages.")

if __name__ == "__main__":
    update_authors()
