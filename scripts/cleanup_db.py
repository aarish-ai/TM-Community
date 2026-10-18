import sqlite3
import time
import os

DB_PATH = os.environ.get("AUTH_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "truth_mirror.db"))

def cleanup_database():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running database cleanup...")
    
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Exiting.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Delete expired verification codes (expires_at is a float timestamp)
        current_time = time.time()
        cursor.execute("DELETE FROM verification_codes WHERE expires_at < ?", (current_time,))
        deleted_codes = cursor.rowcount
        
        # 2. Delete users who registered more than 24 hours ago but never verified
        # created_at is a SQLite CURRENT_TIMESTAMP (UTC string)
        cursor.execute("DELETE FROM users WHERE is_verified = 0 AND created_at < datetime('now', '-24 hours')")
        deleted_users = cursor.rowcount
        
        conn.commit()
        print(f"Cleanup complete: Deleted {deleted_codes} expired codes and {deleted_users} unverified stale users.")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    cleanup_database()
