"""
Model Cache Module

Stores and retrieves cached model information for faster lookups.
Allows Model Linker to find models even across drives and after restarts.
"""

import os
import json
import logging
import time
from typing import List, Dict, Optional
from pathlib import Path


def get_cache_path() -> Path:
    """
    Get the path to the cache file.
    Uses ComfyUI's user directory if available, otherwise falls back to config directory.
    """
    try:
        import folder_paths
        # Try to get user directory from folder_paths
        if hasattr(folder_paths, 'get_user_directory'):
            user_dir = folder_paths.get_user_directory()
            if user_dir:
                return Path(user_dir) / "model_linker_cache.json"
    except:
        pass
    
    # Fallback: use ComfyUI base directory or config directory
    try:
        # Try to find ComfyUI base directory
        import folder_paths
        if hasattr(folder_paths, 'base_path'):
            base_path = folder_paths.base_path
            if base_path:
                return Path(base_path) / "user" / "model_linker_cache.json"
    except:
        pass
    
    # Last resort: use the Model Linker directory
    cache_file = Path(__file__).parent.parent / "model_linker_cache.json"
    return cache_file


def load_cache() -> Dict:
    """
    Load the model cache from disk.
    
    Returns:
        Dictionary with cache data:
        {
            'models': [list of model dicts],
            'last_updated': timestamp,
            'version': cache format version
        }
    """
    cache_path = get_cache_path()
    
    if not cache_path.exists():
        return {
            'models': [],
            'last_updated': 0,
            'version': 1
        }
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            
        # Validate cache structure
        if not isinstance(cache_data, dict):
            return {'models': [], 'last_updated': 0, 'version': 1}
        
        # Ensure required fields exist
        if 'models' not in cache_data:
            cache_data['models'] = []
        if 'last_updated' not in cache_data:
            cache_data['last_updated'] = 0
        if 'version' not in cache_data:
            cache_data['version'] = 1
        
        logging.info(f"Model Linker: Loaded cache with {len(cache_data.get('models', []))} models")
        return cache_data
        
    except Exception as e:
        logging.warning(f"Model Linker: Failed to load cache: {e}")
        return {'models': [], 'last_updated': 0, 'version': 1}


def save_cache(models: List[Dict], metadata: Optional[Dict] = None) -> bool:
    """
    Save the model cache to disk.
    
    Args:
        models: List of model dictionaries to cache
        metadata: Optional metadata to store (e.g., scan duration)
        
    Returns:
        True if saved successfully, False otherwise
    """
    cache_path = get_cache_path()
    
    # Ensure directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    cache_data = {
        'models': models,
        'last_updated': time.time(),
        'version': 1,
        'count': len(models)
    }
    
    if metadata:
        cache_data['metadata'] = metadata
    
    try:
        # Write to temporary file first, then rename (atomic write)
        temp_path = cache_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        temp_path.replace(cache_path)
        
        logging.info(f"Model Linker: Saved cache with {len(models)} models to {cache_path}")
        return True
        
    except Exception as e:
        logging.error(f"Model Linker: Failed to save cache: {e}")
        return False


def should_refresh_cache(config: Dict) -> bool:
    """
    Check if cache should be refreshed based on config settings.
    
    Args:
        config: Configuration dictionary with cache settings
        
    Returns:
        True if cache should be refreshed, False otherwise
    """
    cache_config = config.get('cache', {})
    
    if not cache_config.get('enabled', True):
        return False
    
    if not cache_config.get('auto_refresh', True):
        return False
    
    cache_data = load_cache()
    last_updated = cache_data.get('last_updated', 0)
    
    if last_updated == 0:
        # No cache exists, should refresh
        return True
    
    refresh_interval = cache_config.get('refresh_interval_hours', 0)
    if refresh_interval == 0:
        # Refresh every startup
        return True
    
    # Check if interval has passed
    hours_since_update = (time.time() - last_updated) / 3600
    return hours_since_update >= refresh_interval


def get_cached_models() -> List[Dict]:
    """
    Get models from cache.
    
    Returns:
        List of cached model dictionaries
    """
    cache_data = load_cache()
    return cache_data.get('models', [])


def merge_models_with_cache(scanned_models: List[Dict], cached_models: List[Dict]) -> List[Dict]:
    """
    Merge newly scanned models with cached models.
    Prioritizes scanned models (they're current), but includes cached models
    that might be on other drives or temporarily unavailable.
    
    Args:
        scanned_models: Models found in current scan
        cached_models: Models from cache
        
    Returns:
        Merged list of models (deduplicated by absolute path)
    """
    # Create a set of scanned model paths for quick lookup
    scanned_paths = {os.path.abspath(m.get('path', '')) for m in scanned_models if m.get('path')}
    
    # Start with scanned models (they're current)
    merged = scanned_models.copy()
    
    # Add cached models that weren't found in scan (might be on other drives)
    for cached_model in cached_models:
        cached_path = os.path.abspath(cached_model.get('path', ''))
        if cached_path and cached_path not in scanned_paths:
            # Verify the cached model still exists
            if os.path.exists(cached_path):
                merged.append(cached_model)
                logging.debug(f"Model Linker: Added cached model from other location: {cached_path}")
    
    return merged

