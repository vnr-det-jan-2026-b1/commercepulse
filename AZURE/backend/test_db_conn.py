import psycopg2
import sys

try:
    print("Trying to connect...")
    conn = psycopg2.connect(
        host="db.gwwhksdelequvapksgqx.supabase.co",
        port=6543,
        dbname="postgres",
        user="postgres",
        password="Abhilash@142",
        sslmode="require",
        connect_timeout=10
    )
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
