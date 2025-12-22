"""
Configuration Loader Module

Dynamically finds and loads Model Linker configuration files.
No hardcoded paths - uses ComfyUI's folder_paths to find user directories.
"""

import os
import logging
from typing import Dict, List, Optional
from pathlib import Path


def find_config_file() -> Optional[Path]:
    """
    Find the Model Linker config file in order of priority:
    1. User's ComfyUI directory (model_linker_config.yaml)
    2. Model Linker directory (model_linker_config.yaml)
    3. Model Linker directory (model_linker_config.yaml.example as template)
    
    Returns:
        Path to config file, or None if not found
    """
    config_name = "model_linker_config.yaml"
    
    # Try to get user directory from folder_paths
    user_dir = None
    try:
        import folder_paths
        if hasattr(folder_paths, 'get_user_directory'):
            user_dir = folder_paths.get_user_directory()
        elif hasattr(folder_paths, 'base_path'):
            # Fallback: try to construct user directory
            base_path = folder_paths.base_path
            if base_path:
                # Common patterns
                possible_user_dirs = [
                    Path(base_path) / "user",
                    Path(base_path).parent / "user",
                    Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "ComfyUI",
                ]
                for pd in possible_user_dirs:
                    if pd.exists():
                        user_dir = str(pd)
                        break
    except:
        pass
    
    # Priority 1: User directory
    if user_dir:
        user_config = Path(user_dir) / config_name
        if user_config.exists():
            logging.info(f"Model Linker: Found config at {user_config}")
            return user_config
    
    # Priority 2: Model Linker directory
    linker_dir = Path(__file__).parent.parent
    linker_config = linker_dir / config_name
    if linker_config.exists():
        logging.info(f"Model Linker: Found config at {linker_config}")
        return linker_config
    
    # Priority 3: Example file (for reference, but won't be used)
    example_config = linker_dir / f"{config_name}.example"
    if example_config.exists():
        logging.debug(f"Model Linker: Found example config at {example_config} (not used)")
    
    return None


def find_extra_models_config() -> Optional[Path]:
    """
    Find ComfyUI's extra_models_config.yaml dynamically.
    Uses folder_paths to locate it, no hardcoded paths.
    
    Returns:
        Path to extra_models_config.yaml, or None if not found
    """
    try:
        import folder_paths
        
        # Try to get user directory
        if hasattr(folder_paths, 'get_user_directory'):
            user_dir = folder_paths.get_user_directory()
            if user_dir:
                config_path = Path(user_dir).parent / "extra_models_config.yaml"
                if config_path.exists():
                    return config_path
        
        # Try common locations relative to base_path
        if hasattr(folder_paths, 'base_path'):
            base_path = folder_paths.base_path
            if base_path:
                possible_paths = [
                    Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "ComfyUI" / "extra_models_config.yaml",
                    Path(base_path).parent / "extra_models_config.yaml",
                    Path(os.path.expanduser("~")) / ".config" / "ComfyUI" / "extra_models_config.yaml",
                ]
                for path in possible_paths:
                    if path.exists():
                        return path
    except:
        pass
    
    return None


def load_config() -> Dict:
    """
    Load Model Linker configuration file.
    
    Returns:
        Configuration dictionary with defaults applied
    """
    config_path = find_config_file()
    
    defaults = {
        'additional_directories': [],
        'cache': {
            'enabled': True,
            'filename': 'model_linker_cache.json',
            'auto_refresh': True,
            'refresh_interval_hours': 0
        },
        'scanning': {
            'max_depth': 0,
            'follow_symlinks': True,
            'skip_hidden': True
        }
    }
    
    if not config_path or not config_path.exists():
        logging.debug("Model Linker: No config file found, using defaults")
        return defaults
    
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f) or {}
        
        # Merge with defaults
        config = defaults.copy()
        config.update(user_config)
        
        # Deep merge nested dicts
        if 'cache' in user_config:
            config['cache'].update(user_config['cache'])
        if 'scanning' in user_config:
            config['scanning'].update(user_config['scanning'])
        
        logging.info(f"Model Linker: Loaded config from {config_path}")
        return config
        
    except ImportError:
        logging.warning("Model Linker: PyYAML not available, cannot load config file")
        return defaults
    except Exception as e:
        logging.warning(f"Model Linker: Failed to load config: {e}")
        return defaults


def get_additional_directories(config: Dict) -> List[str]:
    """
    Get list of additional directories to scan from config.
    Resolves relative paths relative to config file location.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of absolute directory paths
    """
    additional = config.get('additional_directories', [])
    if not additional:
        return []
    
    # Get config file location for resolving relative paths
    config_path = find_config_file()
    base_dir = config_path.parent if config_path else Path.cwd()
    
    resolved_paths = []
    for path_str in additional:
        if not path_str or not isinstance(path_str, str):
            continue
        
        # Resolve path
        path = Path(path_str)
        if not path.is_absolute():
            # Relative to config file directory
            path = base_dir / path
        
        abs_path = path.resolve()
        if abs_path.exists() and abs_path.is_dir():
            resolved_paths.append(str(abs_path))
            logging.debug(f"Model Linker: Added additional directory: {abs_path}")
        else:
            logging.warning(f"Model Linker: Additional directory not found or invalid: {path_str}")
    
    return resolved_paths

