import os
import pickle
import time
from helpers import get_logger

logger = get_logger()
CACHE_DIR = ".cache"
REPO_CACHE_FILE = os.path.join(CACHE_DIR, "repositories.pkl")
CACHE_EXPIRY = 60 * 60 * 24 * 7  # 7 days in seconds

def ensure_cache_dir():
    """Ensure the cache directory exists."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        logger.info(f"Created cache directory: {CACHE_DIR}")

def save_repositories_to_cache(repositories):
    """Save repositories to cache."""
    ensure_cache_dir()
    try:
        with open(REPO_CACHE_FILE, 'wb') as f:
            pickle.dump(repositories, f)
        logger.info(f"Saved {len(repositories)} repositories to cache")
        return True
    except Exception as e:
        logger.error(f"Failed to save repositories to cache: {e}")
        return False

def load_repositories_from_cache():
    """Load repositories from cache if available and not expired."""
    if not os.path.exists(REPO_CACHE_FILE):
        logger.info("Cache file does not exist")
        return None
    
    # Check if cache is expired
    cache_age = time.time() - os.path.getmtime(REPO_CACHE_FILE)
    if cache_age > CACHE_EXPIRY:
        logger.info(f"Cache is expired (age: {cache_age/3600:.1f} hours)")
        return None
    
    try:
        with open(REPO_CACHE_FILE, 'rb') as f:
            repositories = pickle.load(f)
        logger.info(f"Loaded {len(repositories)} repositories from cache")
        return repositories
    except Exception as e:
        logger.error(f"Failed to load repositories from cache: {e}")
        return None

def clear_cache():
    """Clear the cache."""
    if os.path.exists(REPO_CACHE_FILE):
        os.remove(REPO_CACHE_FILE)
        logger.info("Cache cleared")
