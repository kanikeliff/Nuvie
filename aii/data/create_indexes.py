import os
import sys
from sqlalchemy import create_engine, text



# Güvenli okuma (Lütfen kendi Connection String'inizi kullanın)
DATABASE_URL = "postgresql://neondb_owner:npg_ANY0Q7uFlZSi@ep-restless-art-ah6dr023-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

try:
    engine = create_engine(DATABASE_URL)
    print("Database connection established.")
except Exception as e:
    print(f"FATAL: Could not establish DB connection. Error: {e}")
    sys.exit(1)

def create_performance_indexes(engine):
    """
    Creates indexes on frequently searched columns (User ID, Movie ID) 
    to drastically improve query performance on the 'ratings' table.
    """
    print("\n[START] Creating performance indexes...")
    
    # 1. ratings tablosu için User ID indexi (Elif ve Berkay bunu çok kullanacak)
    index_user_id = text("CREATE INDEX IF NOT EXISTS idx_ratings_user ON ratings (user_id);")
    
    # 2. ratings tablosu için Movie ID indexi
    index_movie_id = text("CREATE INDEX IF NOT EXISTS idx_ratings_movie ON ratings (movie_id);")

    # 3. ratings tablosu için hem User hem Movie ID indexi (En popüler AI sorguları için)
    index_compound = text("CREATE INDEX IF NOT EXISTS idx_ratings_compound ON ratings (user_id, movie_id);")
    
    # 4. movies tablosu için Movie ID indexi
    index_movies_id = text("CREATE INDEX IF NOT EXISTS idx_movies_id ON movies (movie_id);")

    
    with engine.begin() as connection:
        connection.execute(index_user_id)
        connection.execute(index_movie_id)
        connection.execute(index_compound)
        connection.execute(index_movies_id)

    print("✅ Indexing complete. Database performance significantly improved for core queries.")
    
if __name__ == '__main__':
    create_performance_indexes(engine)
    print("\n--------------------------------------------------")
