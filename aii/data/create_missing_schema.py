
import os
import sys
from sqlalchemy import create_engine, text


# Kendi Connection String'inizi buraya yapıştırın
DATABASE_URL = "postgresql://neondb_owner:npg_ANY0Q7uFlZSi@ep-restless-art-ah6dr023-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

try:
    engine = create_engine(DATABASE_URL)
    print("Database connection established.")
except Exception as e:
    print(f"FATAL: Could not establish DB connection. Error: {e}")
    sys.exit(1)

def create_remaining_tables(engine):
    """
    Creates the necessary tables for social features, watch logs, 
    and the personalized feed, which are not included in MovieLens.
    """
    print("\n[START] Creating missing social and log schemas...")

    # 1. FRIENDS Tablosu (Sosyal İlişki)
    # Kimin kiminle arkadaş olduğunu tutar.
    friends_table = text("""
        CREATE TABLE IF NOT EXISTS friends (
            user_id_1 INTEGER REFERENCES users(user_id),
            user_id_2 INTEGER REFERENCES users(user_id),
            status VARCHAR(20) NOT NULL, -- Örn: 'pending', 'accepted', 'blocked'
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (user_id_1, user_id_2)
        );
    """)

    # 2. WATCH_EVENTS Tablosu (Kullanıcı Davranış Logları)
    # Kullanıcının ne zaman bir filmi izlemeye başladığı/bitirdiği gibi canlı geri bildirim verileri.
    watch_events_table = text("""
        CREATE TABLE IF NOT EXISTS watch_events (
            event_id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            movie_id INTEGER REFERENCES movies(movie_id),
            event_type VARCHAR(50) NOT NULL, -- Örn: 'started', 'completed', 'paused'
            progress_percent INTEGER,
            timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
    """)

    # 3. RECOMMENDATION_FEED Tablosu (Canlı Öneri Sonuçlarını Saklama)
    # AI servisinin hesapladığı ve kullanıcının görmesi gereken önerilerin sırasını tutar.
    recommendation_feed_table = text("""
        CREATE TABLE IF NOT EXISTS recommendation_feed (
            feed_id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE REFERENCES users(user_id),
            movie_id_list INTEGER[], -- Öneri listesini dizi olarak saklama
            last_calculated TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
    """)
    
    with engine.begin() as connection:
        connection.execute(friends_table)
        connection.execute(watch_events_table)
        connection.execute(recommendation_feed_table)

    print("✅ Missing schemas (friends, watch_events, recommendation_feed) created.")
    
if __name__ == '__main__':
    create_remaining_tables(engine)
    print("\n--------------------------------------------------")
