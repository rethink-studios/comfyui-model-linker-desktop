"""
Workflow Analyzer Module

Extracts model references from workflow JSON and identifies missing models.
Supports both API format and Graph format workflows.
"""

import os
import logging
from typing import List, Dict, Any, Optional

# Import folder_paths lazily - it may not be available until ComfyUI is initialized
try:
    import folder_paths
except ImportError:
    folder_paths = None
    logging.warning("Model Linker: folder_paths not available yet - will retry later")


# Common model file extensions
MODEL_EXTENSIONS = {'.ckpt', '.pt', '.pt2', '.bin', '.pth', '.safetensors', '.pkl', '.sft', '.onnx'}

# Mapping of common node types to their expected model category
NODE_TYPE_TO_CATEGORY_HINTS = {
    'CheckpointLoaderSimple': 'checkpoints',
    'CheckpointLoader': 'checkpoints',
    'unCLIPCheckpointLoader': 'checkpoints',
    'VAELoader': 'vae',
    'LoraLoader': 'loras',
    'LoraLoaderModelOnly': 'loras',
    'UNETLoader': 'diffusion_models',  # UNETLoader uses diffusion_models category
    'ControlNetLoader': 'controlnet',
    'ControlNetLoaderAdvanced': 'controlnet',
    'CLIPLoader': 'text_encoders',  # CLIPLoader typically uses text_encoders
    'CLIPVisionLoader': 'clip_vision',
    'UpscaleModelLoader': 'upscale_models',
    'HypernetworkLoader': 'hypernetworks',
    'EmbeddingLoader': 'embeddings',
}

# Common input field names that contain model references
MODEL_INPUT_FIELDS = {
    'ckpt_name', 'checkpoint_name', 'model_name',
    'vae_name', 'lora_name', 'unet_name', 'clip_name',
    'control_net_name', 'controlnet_name',
    'upscale_model', 'hypernetwork_name', 'embedding_name'
}


def is_model_filename(value: Any) -> bool:
    """
    Check if a value looks like a model filename.
    
    Args:
        value: The value to check
        
    Returns:
        True if it looks like a model filename
    """
    if not isinstance(value, str):
        return False
    
    # Check if it ends with a model extension
    _, ext = os.path.splitext(value.lower())
    return ext in MODEL_EXTENSIONS


def try_resolve_model_path(value: str, categories: List[str] = None) -> Optional[tuple[str, str]]:
    """
    Try to resolve a model path using folder_paths.
    
    Args:
        value: The model filename/path to resolve
        categories: Optional list of categories to try (if None, tries all)
        
    Returns:
        Tuple of (category, full_path) if found, None otherwise
    """
    if not isinstance(value, str) or not value.strip():
        return None
    
    # Remove any path separators that might indicate an absolute path prefix
    filename = value.strip()
    
    # Ensure folder_paths is available
    global folder_paths
    if folder_paths is None:
        try:
            import folder_paths as fp
            folder_paths = fp
        except ImportError:
            logging.error("Model Linker: folder_paths not available")
            return None
    
    # If categories not provided, try all categories
    if categories is None:
        categories = list(folder_paths.folder_names_and_paths.keys())
    
    # Skip non-model categories
    skip_categories = {'custom_nodes', 'configs'}
    categories = [c for c in categories if c not in skip_categories]
    
    for category in categories:
        try:
            full_path = folder_paths.get_full_path(category, filename)
            if full_path and os.path.exists(full_path):
                return (category, full_path)
        except Exception:
            continue
    
    return None


def detect_workflow_format(workflow_json: Dict[str, Any]) -> str:
    """
    Detect if workflow is in API format or Graph format.
    
    Args:
        workflow_json: Workflow JSON dictionary
        
    Returns:
        'api' or 'graph'
    """
    # API format: keys are node IDs (numbers as strings), values have 'class_type' and 'inputs'
    # Graph format: has 'nodes' array with objects containing 'type' and 'widgets_values'
    
    if 'nodes' in workflow_json and isinstance(workflow_json['nodes'], list):
        return 'graph'
    
    # Check if it looks like API format
    for key, value in workflow_json.items():
        if isinstance(value, dict) and 'class_type' in value and 'inputs' in value:
            return 'api'
    
    return 'unknown'


def get_node_model_info_api(node_id: str, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract model references from a single node in API format.
    
    Args:
        node_id: Node ID (string)
        node_data: Node data dictionary with 'class_type' and 'inputs'
        
    Returns:
        List of model reference dictionaries
    """
    model_refs = []
    class_type = node_data.get('class_type', '')
    inputs = node_data.get('inputs', {})
    
    if not inputs:
        return model_refs
    
    # Get category hints for this node type
    category_hint = NODE_TYPE_TO_CATEGORY_HINTS.get(class_type)
    categories_to_try = [category_hint] if category_hint else None
    
    # Check each input field for model references
    for field_name, value in inputs.items():
        # Skip non-string values and connection references (lists)
        if not isinstance(value, str):
            continue
            
        # Check if this field name suggests it's a model reference
        is_model_field = (field_name.lower() in MODEL_INPUT_FIELDS or 
                         field_name.lower().endswith('_name') or
                         is_model_filename(value))
        
        if not is_model_field:
            continue
        
        # Try to resolve the model path
        resolved = try_resolve_model_path(value, categories_to_try)
        
        if resolved:
            category, full_path = resolved
            exists = os.path.exists(full_path)
        else:
            # If we can't resolve it, check if it at least looks like a model filename
            category = category_hint or 'unknown'
            full_path = None
            exists = False
        
        model_refs.append({
            'node_id': node_id,
            'node_type': class_type,
            'widget_index': field_name,  # For API format, use field name instead of index
            'field_name': field_name,
            'original_path': value,
            'category': category,
            'full_path': full_path,
            'exists': exists
        })
    
    return model_refs


def get_node_model_info_graph(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract model references from a single node in Graph format.
    
    Args:
        node: Node dictionary from workflow JSON
        
    Returns:
        List of model reference dictionaries
    """
    model_refs = []
    node_id = node.get('id')
    node_type = node.get('type', '')
    widgets_values = node.get('widgets_values', [])
    
    if not widgets_values:
        return model_refs
    
    # Get category hints for this node type
    category_hint = NODE_TYPE_TO_CATEGORY_HINTS.get(node_type)
    categories_to_try = [category_hint] if category_hint else None
    
    # For each widget value, check if it looks like a model file
    for idx, value in enumerate(widgets_values):
        if not is_model_filename(value):
            continue
        
        # Try to resolve the model path
        resolved = try_resolve_model_path(value, categories_to_try)
        
        if resolved:
            category, full_path = resolved
            exists = os.path.exists(full_path)
        else:
            category = category_hint or 'unknown'
            full_path = None
            exists = False
        
        model_refs.append({
            'node_id': node_id,
            'node_type': node_type,
            'widget_index': idx,
            'original_path': value,
            'category': category,
            'full_path': full_path,
            'exists': exists
        })
    
    return model_refs


def analyze_workflow_models(workflow_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all model references from a workflow, supporting both API and Graph formats.
    
    Args:
        workflow_json: Complete workflow JSON dictionary
        
    Returns:
        List of model reference dictionaries
    """
    all_model_refs = []
    
    # Detect workflow format
    format_type = detect_workflow_format(workflow_json)
    logging.info(f"Model Linker: Detected workflow format: {format_type}")
    
    if format_type == 'api':
        # API format: iterate through top-level keys as node IDs
        for node_id, node_data in workflow_json.items():
            if isinstance(node_data, dict) and 'class_type' in node_data:
                try:
                    model_refs = get_node_model_info_api(node_id, node_data)
                    all_model_refs.extend(model_refs)
                except Exception as e:
                    logging.warning(f"Error analyzing API node {node_id}: {e}")
                    continue
                    
    elif format_type == 'graph':
        # Graph format: analyze nodes array
        nodes = workflow_json.get('nodes', [])
        for node in nodes:
            try:
                model_refs = get_node_model_info_graph(node)
                all_model_refs.extend(model_refs)
            except Exception as e:
                logging.warning(f"Error analyzing graph node {node.get('id', 'unknown')}: {e}")
                continue
                
        # Also check for subgraphs in definitions
        definitions = workflow_json.get('definitions', {})
        subgraphs = definitions.get('subgraphs', [])
        
        for subgraph in subgraphs:
            subgraph_id = subgraph.get('id')
            subgraph_name = subgraph.get('name', subgraph_id)
            subgraph_nodes = subgraph.get('nodes', [])
            
            for node in subgraph_nodes:
                try:
                    model_refs = get_node_model_info_graph(node)
                    # Mark as belonging to this subgraph
                    for ref in model_refs:
                        ref['subgraph_id'] = subgraph_id
                        ref['subgraph_name'] = subgraph_name
                        ref['is_top_level'] = False
                    all_model_refs.extend(model_refs)
                except Exception as e:
                    logging.warning(f"Error analyzing subgraph node {node.get('id', 'unknown')}: {e}")
                    continue
    else:
        logging.warning(f"Model Linker: Unknown workflow format: {format_type}")
    
    logging.info(f"Model Linker: Found {len(all_model_refs)} model references")
    return all_model_refs


def identify_missing_models(
    workflow_models: List[Dict[str, Any]],
    available_models: List[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Identify which models from the workflow are missing.
    
    Args:
        workflow_models: List of model references from analyze_workflow_models
        available_models: Optional list of available models (if None, checks via folder_paths)
        
    Returns:
        List of missing model references (filtered to only missing ones)
    """
    missing = []
    
    for model_ref in workflow_models:
        # If exists is False, it's missing
        if not model_ref.get('exists', False):
            missing.append(model_ref)
    
    return missing