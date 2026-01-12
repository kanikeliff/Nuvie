import os
import sys
from sqlalchemy import create_engine, text


# Kendi Connection String'inizi buraya yapıştırın
DATABASE_URL = "postgresql://neondb_owner:npg_ANY0Q7uFlZSi@ep-restless-art-ah6dr023-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

try:
    engine = create_engine(DATABASE_URL)
    print("Database connection established for key fix.")
except Exception as e:
    print(f"FATAL: DB connection error. Error: {e}")
    sys.exit(1)

def fix_missing_primary_keys(engine):
    """
    Sets the user_id and movie_id columns as PRIMARY KEYs to enable Foreign Key constraints.
    """
    print("\n[START] Fixing missing Primary Keys...")
    
    # users tablosunda user_id'yi Primary Key yapma
    fix_users_pk = text("ALTER TABLE users ADD PRIMARY KEY (user_id);")
    
    # movies tablosunda movie_id'yi Primary Key yapma (Gelecekteki FK'lar için)
    fix_movies_pk = text("ALTER TABLE movies ADD PRIMARY KEY (movie_id);")
    
    # ratings tablosuna da bileşik Primary Key ekleme (Tekrarlayan puanlamaları engeller)
    fix_ratings_pk = text("ALTER TABLE ratings ADD PRIMARY KEY (user_id, movie_id);")
    

    with engine.begin() as connection:
        # Hata vermemesi için mevcut olabilecek Primary Key'i önce kaldırmamız gerekir, 
        # ancak MovieLens ETL'de PK eklemediğimiz için direkt ekleyebiliriz.
        
        connection.execute(fix_users_pk)
        print("-> PRIMARY KEY added to 'users' (user_id).")
        
        connection.execute(fix_movies_pk)
        print("-> PRIMARY KEY added to 'movies' (movie_id).")
        
        connection.execute(fix_ratings_pk)
        print("-> PRIMARY KEY added to 'ratings' (user_id, movie_id).")

    print("✅ Primary Key fix complete.")
    
if __name__ == '__main__':
    fix_missing_primary_keys(engine)
    print("\n--------------------------------------------------")
