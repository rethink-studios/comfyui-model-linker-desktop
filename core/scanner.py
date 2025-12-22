"""
Directory Scanner Module

Scans configured model directories and finds available model files.
"""

import os
import logging
from typing import List, Dict, Tuple

# Import folder_paths lazily - it may not be available until ComfyUI is initialized
try:
    import folder_paths
except ImportError:
    folder_paths = None
    logging.warning("Model Linker: folder_paths not available yet - will retry later")

# Model file extensions to look for
# This matches folder_paths.supported_pt_extensions
MODEL_EXTENSIONS = {'.ckpt', '.pt', '.pt2', '.bin', '.pth', '.safetensors', '.pkl', '.sft', '.onnx'}


def get_model_directories() -> Dict[str, Tuple[List[str], set]]:
    """
    Get all configured model directories from folder_paths.
    Also checks extra_models_config.yaml for additional paths.
    
    Returns:
        Dictionary mapping category name to (list of paths, set of extensions)
    """
    global folder_paths
    
    if folder_paths is None:
        # Try to import again
        try:
            import folder_paths as fp
            folder_paths = fp
        except ImportError:
            logging.error("Model Linker: folder_paths still not available")
            return {}
    
    # Get base directories from folder_paths
    directories = folder_paths.folder_names_and_paths.copy()
    
    # Also check for extra_model_paths.yaml to ensure we get all configured paths
    # This is important for ComfyUI Desktop which uses extra_models_config.yaml
    try:
        import yaml
        import os
        
        # Try to find extra_models_config.yaml in common locations
        config_paths = [
            os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "ComfyUI", "extra_models_config.yaml"),
            os.path.join(os.path.expanduser("~"), ".config", "ComfyUI", "extra_models_config.yaml"),
        ]
        
        # Also check if folder_paths has a method to get extra paths
        if hasattr(folder_paths, 'get_extra_model_paths'):
            extra_paths = folder_paths.get_extra_model_paths()
            if extra_paths:
                for category, paths in extra_paths.items():
                    if category in directories:
                        # Merge paths, avoiding duplicates
                        existing_paths, extensions = directories[category]
                        for path in paths:
                            if path not in existing_paths:
                                existing_paths.append(path)
                    else:
                        # New category
                        directories[category] = (paths, set())
        
        # Try to load from YAML file directly
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        if config:
                            for config_name, config_data in config.items():
                                if isinstance(config_data, dict) and 'base_path' in config_data:
                                    base_path = config_data.get('base_path', '')
                                    if base_path and os.path.exists(base_path):
                                        # Process each category in this config
                                        for category, rel_path in config_data.items():
                                            if category != 'base_path' and category != 'is_default':
                                                full_path = os.path.join(base_path, rel_path)
                                                if os.path.exists(full_path):
                                                    # Add to directories
                                                    if category in directories:
                                                        existing_paths, extensions = directories[category]
                                                        if full_path not in existing_paths:
                                                            existing_paths.append(full_path)
                                                            logging.debug(f"Added extra path: {category} -> {full_path}")
                                                    else:
                                                        directories[category] = ([full_path], set())
                except Exception as e:
                    logging.debug(f"Could not load extra_models_config.yaml from {config_path}: {e}")
                break  # Only try first existing file
    except ImportError:
        # yaml not available, skip extra config loading
        pass
    except Exception as e:
        logging.debug(f"Error loading extra model paths: {e}")
    
    return directories


def scan_directory(directory: str, extensions: set, category: str) -> List[Dict[str, str]]:
    """
    Recursively scan a single directory for model files.
    
    Args:
        directory: Absolute path to directory to scan
        extensions: Set of file extensions to look for
        category: Model category name (e.g., 'checkpoints', 'loras')
        
    Returns:
        List of dictionaries with model information:
        {
            'filename': 'model.safetensors',
            'path': 'absolute/path/to/model.safetensors',
            'relative_path': 'subfolder/model.safetensors' or 'model.safetensors',
            'category': 'checkpoints',
            'base_directory': 'absolute/path/to/base'
        }
    """
    models = []
    
    if not os.path.exists(directory) or not os.path.isdir(directory):
        logging.debug(f"Directory does not exist or is not accessible: {directory}")
        return models
    
    try:
        # Get absolute path and normalize
        base_directory = os.path.abspath(directory)
        
        # Walk through directory recursively
        for root, dirs, files in os.walk(base_directory, followlinks=True):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for filename in files:
                # Check if file has a model extension
                file_ext = os.path.splitext(filename)[1].lower()
                
                # For categories with empty extension set, accept all files
                # Otherwise, check if extension matches
                if len(extensions) == 0 or file_ext in extensions or file_ext in MODEL_EXTENSIONS:
                    full_path = os.path.join(root, filename)
                    
                    # Calculate relative path from base directory
                    # IMPORTANT: Use OS-native path separators (backslashes on Windows)
                    # This matches ComfyUI's recursive_search format for get_filename_list
                    try:
                        relative_path = os.path.relpath(full_path, base_directory)
                        # DO NOT normalize - keep OS-native separators to match ComfyUI
                        # ComfyUI's get_filename_list uses os.path.relpath which returns
                        # backslashes on Windows, forward slashes on Unix
                    except ValueError:
                        # If paths are on different drives (Windows), use filename only
                        relative_path = filename
                    
                    models.append({
                        'filename': filename,
                        'path': full_path,
                        'relative_path': relative_path,
                        'category': category,
                        'base_directory': base_directory
                    })
    except (OSError, PermissionError) as e:
        logging.warning(f"Error scanning directory {directory}: {e}")
    
    return models


def scan_all_directories() -> List[Dict[str, str]]:
    """
    Scan all configured model directories and return list of available models.
    
    Returns:
        List of dictionaries with model information (same format as scan_directory)
    """
    all_models = []
    directories = get_model_directories()
    
    logging.info(f"Model Linker: Scanning {len(directories)} model categories")
    
    for category, (paths, extensions) in directories.items():
        # Skip categories that aren't typically model directories
        if category in ['custom_nodes', 'configs']:
            continue
            
        for directory_path in paths:
            try:
                # Normalize path
                if not os.path.isabs(directory_path):
                    # If relative, try to resolve it
                    directory_path = os.path.abspath(directory_path)
                
                models = scan_directory(directory_path, extensions, category)
                all_models.extend(models)
                logging.info(f"Model Linker: Found {len(models)} models in {category} -> {directory_path}")
            except Exception as e:
                logging.warning(f"Model Linker: Error scanning {category} directory {directory_path}: {e}")
    
    logging.info(f"Model Linker: Total models found: {len(all_models)}")
    return all_models


def get_model_files() -> List[Dict[str, str]]:
    """
    Get list of all available model files with metadata.
    
    This is the main entry point for getting model files.
    
    Returns:
        List of model dictionaries (same format as scan_directory)
    """
    return scan_all_directories()

