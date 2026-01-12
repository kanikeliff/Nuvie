import os
import sys
import pandas as pd
from sqlalchemy import create_engine


# --- 1. CONFIGURATION (DATABASE CONNECTION) ---
# NOTE: In a professional environment, this URL must be loaded securely from an environment 
# variable (e.g., from a .env file or Docker secrets), not hardcoded.
DATABASE_URL = os.environ.get('DATABASE_URL')
# Define the absolute path to the data files, assuming the script is in '.../data/'
# This resolves the previous "No such file or directory" error by using a relative path.
DATA_DIR = os.path.join(os.path.dirname(__file__), '') 

try:
    # Create the SQLAlchemy engine for PostgreSQL connection
    engine = create_engine(DATABASE_URL)
    print("Database connection engine successfully prepared.")
except Exception as e:
    print(f"FATAL: Could not establish database connection. Error: {e}")
    sys.exit(1)

# ----------------------------------------------------------------------

def load_ratings():
    """
    Handles the Extract, Transform, and Load (ETL) process for the MovieLens 
    ratings data into the 'ratings' table.
    """
    print("\n[START] Processing ratings.dat...")
    
    # Define columns for the MovieLens ratings.dat file
    r_cols = ['user_id', 'movie_id', 'rating', 'timestamp']
    
    # EXTRACT & TRANSFORM: Read the .dat file using Pandas
    ratings = pd.read_csv(
        os.path.join(DATA_DIR, 'ratings.dat'), 
        sep='::', 
        names=r_cols, 
        engine='python',
        encoding='latin-1' 
    )
    
    # Data Validation
    total_rows = len(ratings)
    print(f"Data extracted successfully. Total rows: {total_rows}")
    
    # LOAD: Write the DataFrame to the PostgreSQL database (Neon)
    ratings.to_sql(
        'ratings',      # Table name
        con=engine,     
        if_exists='replace', # Drop and recreate the table
        index=False     
    )
    print("SUCCESS: 'ratings' table loaded.")
    return total_rows

# ----------------------------------------------------------------------

def load_movies():
    """Reads and loads movies.dat into the 'movies' table."""
    
    print("\n[START] Processing movies.dat...")
    m_cols = ['movie_id', 'title', 'genres']
    
    # EXTRACT & TRANSFORM
    movies = pd.read_csv(
        os.path.join(DATA_DIR, 'movies.dat'), 
        sep='::', 
        names=m_cols, 
        engine='python',
        encoding='latin-1' 
    )
    
    total_rows = len(movies)
    print(f"Data extracted successfully. Total rows: {total_rows}")
    
    # LOAD
    movies.to_sql(
        'movies',       # Table name
        con=engine,     
        if_exists='replace', 
        index=False     
    )
    print("SUCCESS: 'movies' table loaded.")
    return total_rows

# ----------------------------------------------------------------------

def load_users():
    """Reads and loads users.dat into the 'users' table."""
    
    print("\n[START] Processing users.dat...")
    u_cols = ['user_id', 'gender', 'age', 'occupation', 'zip_code']
    
    # EXTRACT & TRANSFORM
    users = pd.read_csv(
        os.path.join(DATA_DIR, 'users.dat'), 
        sep='::', 
        names=u_cols, 
        engine='python',
        encoding='latin-1' 
    )
    
    total_rows = len(users)
    print(f"Data extracted successfully. Total rows: {total_rows}")
    
    # LOAD
    users.to_sql(
        'users',        # Table name
        con=engine,     
        if_exists='replace', 
        index=False     
    )
    print("SUCCESS: 'users' table loaded.")
    return total_rows

# ----------------------------------------------------------------------

def verify_load(expected_ratings, expected_movies, expected_users):
    """Verifies the row counts in the database against expected values."""
    print("\n[VERIFICATION] Querying database for final row counts...")
    
    # Query the counts from the database
    ratings_count_db = pd.read_sql("SELECT COUNT(*) FROM ratings", con=engine).iloc[0, 0]
    movies_count_db = pd.read_sql("SELECT COUNT(*) FROM movies", con=engine).iloc[0, 0]
    users_count_db = pd.read_sql("SELECT COUNT(*) FROM users", con=engine).iloc[0, 0]
    
    # Output the results
    print("--- FINAL DATASET STATUS ---")
    print(f"Ratings Count (DB): {ratings_count_db} | Expected: {expected_ratings}")
    print(f"Movies Count (DB): {movies_count_db} | Expected: {expected_movies}")
    print(f"Users Count (DB): {users_count_db} | Expected: {expected_users}")
    
    if ratings_count_db == expected_ratings and movies_count_db == expected_movies and users_count_db == expected_users:
        print("\n[STATUS: SUCCESS] All core MovieLens tables loaded and verified.")
        return True
    else:
        print("\n[STATUS: WARNING] Row counts do not match expected values. Review ETL logs.")
        return False
        
# ----------------------------------------------------------------------

if __name__ == '__main__':
    print("\n--- STARTING FULL MOVIELENS DATA LOAD PROCESS (ETL) ---")
    
    try:
        # Load all tables sequentially
        ratings_count = load_ratings()
        movies_count = load_movies()
        users_count = load_users()
        
        # Verify the load process
        verify_load(ratings_count, movies_count, users_count)
        
    except Exception as e:
        print("\nFATAL ERROR: ETL process failed during execution.")
        print(f"Ensure all .dat files are in the {DATA_DIR} directory. Error details: {e}")
        
    print("--------------------------------------------------")
