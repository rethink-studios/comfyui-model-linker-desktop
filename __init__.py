"""
@author: Model Linker Team (Desktop Fork by RETHINK Studios)
@title: ComfyUI Model Linker - Desktop Edition
@nickname: Model Linker
@version: 2.2.0
@description: Extension for relinking missing models in ComfyUI workflows with intelligent matching and integrated downloads
"""

import logging
import threading
import time
import asyncio
import aiohttp
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ModelLinker")
logger.setLevel(logging.INFO)

# Track active downloads for cancellation
active_downloads = {}

# Web directory for JavaScript interface
WEB_DIRECTORY = "./web"

# Empty NODE_CLASS_MAPPINGS - we don't provide custom nodes, only web extension
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["WEB_DIRECTORY", "NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

# Track if routes have been set up
_routes_registered = False


def register_api_routes():
    """
    Register the Model Linker API routes with ComfyUI's server.
    This function is designed to work with ComfyUI Desktop.
    """
    global _routes_registered
    
    if _routes_registered:
        logger.debug("Model Linker: Routes already registered")
        return True
    
    try:
        from aiohttp import web
    except ImportError:
        logger.error("Model Linker: aiohttp not available")
        return False
    
    # Try to get PromptServer
    try:
        from server import PromptServer
    except ImportError:
        logger.error("Model Linker: Cannot import PromptServer")
        return False
    
    # Check if PromptServer.instance exists and has an app
    if not hasattr(PromptServer, 'instance') or PromptServer.instance is None:
        logger.debug("Model Linker: PromptServer.instance not ready yet")
        return False
    
    if not hasattr(PromptServer.instance, 'app') or PromptServer.instance.app is None:
        logger.debug("Model Linker: PromptServer.instance.app not ready yet")
        return False
    
    # Import core modules
    try:
        from .core.linker import analyze_and_find_matches, apply_resolution
        from .core.scanner import get_model_files
    except ImportError as e:
        logger.error(f"Model Linker: Could not import core modules: {e}")
        return False
    
    # Define route handlers
    async def analyze_workflow(request):
        """Analyze workflow and return missing models with matches."""
        try:
            data = await request.json()
            workflow_json = data.get('workflow')
            
            if not workflow_json:
                return web.json_response({'error': 'Workflow JSON is required'}, status=400)
            
            result = analyze_and_find_matches(workflow_json)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Model Linker analyze error: {e}", exc_info=True)
            return web.json_response({'error': str(e)}, status=500)
    
    async def resolve_models(request):
        """Apply model resolution and return updated workflow."""
        try:
            data = await request.json()
            workflow_json = data.get('workflow')
            resolutions = data.get('resolutions', [])
            
            if not workflow_json:
                return web.json_response({'error': 'Workflow JSON is required'}, status=400)
            
            if not resolutions:
                return web.json_response({'error': 'Resolutions array is required'}, status=400)
            
            updated_workflow = apply_resolution(workflow_json, resolutions)
            return web.json_response({'workflow': updated_workflow, 'success': True})
        except Exception as e:
            logger.error(f"Model Linker resolve error: {e}", exc_info=True)
            return web.json_response({'error': str(e), 'success': False}, status=500)
    
    async def get_models(request):
        """Get list of all available models."""
        try:
            # Check if cache refresh is requested
            use_cache = request.query.get('use_cache', 'true').lower() != 'false'
            models = get_model_files(use_cache=use_cache)
            return web.json_response(models)
        except Exception as e:
            logger.error(f"Model Linker get_models error: {e}", exc_info=True)
            return web.json_response({'error': str(e)}, status=500)
    
    async def refresh_cache(request):
        """Force refresh the model cache."""
        try:
            from .core.scanner import scan_all_directories
            from .core.cache import save_cache
            
            logger.info("Model Linker: Manual cache refresh requested")
            models = scan_all_directories(use_cache=False)
            save_cache(models, {'manual_refresh': True})
            
            return web.json_response({
                'success': True,
                'models_found': len(models),
                'message': f'Cache refreshed with {len(models)} models'
            })
        except Exception as e:
            logger.error(f"Model Linker refresh_cache error: {e}", exc_info=True)
            return web.json_response({'error': str(e), 'success': False}, status=500)
    
    async def health_check(request):
        """Health check endpoint to verify Model Linker is running."""
        return web.json_response({'status': 'ok', 'version': '2.2.0'})
    
    async def download_model(request):
        """Download a model from a URL with progress tracking."""
        try:
            data = await request.json()
            url = data.get('url')
            category = data.get('category', 'checkpoints')
            filename = data.get('filename')
            download_id = data.get('download_id')
            
            if not url or not filename or not download_id:
                return web.json_response({'error': 'url, filename, and download_id are required'}, status=400)
            
            # Determine destination path based on category
            import folder_paths
            model_dirs = folder_paths.get_folder_paths(category)
            if not model_dirs:
                return web.json_response({'error': f'No directory found for category: {category}'}, status=400)
            
            dest_dir = Path(model_dirs[0])
            dest_path = dest_dir / filename
            
            # Check if file already exists
            if dest_path.exists():
                return web.json_response({'error': 'File already exists', 'path': str(dest_path)}, status=409)
            
            # Create directory if it doesn't exist
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Start download in background
            download_task = asyncio.create_task(
                _download_file_with_progress(url, dest_path, download_id)
            )
            
            # Store task for cancellation
            active_downloads[download_id] = {
                'task': download_task,
                'cancelled': False,
                'progress': {'downloaded': 0, 'total': 0, 'percent': 0}
            }
            
            return web.json_response({
                'success': True,
                'download_id': download_id,
                'destination': str(dest_path)
            })
        except Exception as e:
            logger.error(f"Model Linker download error: {e}", exc_info=True)
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_download_progress(request):
        """Get progress of an active download."""
        try:
            download_id = request.match_info.get('download_id')
            
            if download_id not in active_downloads:
                return web.json_response({'error': 'Download not found'}, status=404)
            
            download_info = active_downloads[download_id]
            progress = download_info['progress']
            
            # Check if download is complete
            if download_info['task'].done():
                try:
                    result = download_info['task'].result()
                    del active_downloads[download_id]
                    return web.json_response({
                        'status': 'completed',
                        'success': True,
                        'result': result
                    })
                except Exception as e:
                    del active_downloads[download_id]
                    return web.json_response({
                        'status': 'failed',
                        'error': str(e)
                    })
            
            return web.json_response({
                'status': 'downloading' if not download_info['cancelled'] else 'cancelling',
                'progress': progress
            })
        except Exception as e:
            logger.error(f"Model Linker progress error: {e}", exc_info=True)
            return web.json_response({'error': str(e)}, status=500)
    
    async def cancel_download(request):
        """Cancel an active download."""
        try:
            download_id = request.match_info.get('download_id')
            
            if download_id not in active_downloads:
                return web.json_response({'error': 'Download not found'}, status=404)
            
            download_info = active_downloads[download_id]
            download_info['cancelled'] = True
            download_info['task'].cancel()
            
            return web.json_response({'success': True, 'message': 'Download cancelled'})
        except Exception as e:
            logger.error(f"Model Linker cancel error: {e}", exc_info=True)
            return web.json_response({'error': str(e)}, status=500)
    
    async def _download_file_with_progress(url: str, dest_path: Path, download_id: str):
        """Download a file with progress tracking."""
        # IMPORTANT: Download to .tmp file first to prevent partial files from being detected!
        temp_path = dest_path.with_suffix(dest_path.suffix + '.tmp')
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download: HTTP {response.status}")
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    # Update progress info
                    if download_id in active_downloads:
                        active_downloads[download_id]['progress']['total'] = total_size
                    
                    # Download to TEMP file first
                    with open(temp_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            # Check if cancelled
                            if download_id in active_downloads and active_downloads[download_id]['cancelled']:
                                # Close and delete temp file
                                f.close()
                                if temp_path.exists():
                                    temp_path.unlink()
                                logger.info(f"Download cancelled, temp file deleted: {temp_path}")
                                raise asyncio.CancelledError("Download cancelled by user")
                            
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress
                            if download_id in active_downloads:
                                progress = active_downloads[download_id]['progress']
                                progress['downloaded'] = downloaded
                                progress['total'] = total_size
                                progress['percent'] = int((downloaded / total_size * 100)) if total_size > 0 else 0
                    
                    # Only rename to final name if download completed successfully!
                    if downloaded == total_size or total_size == 0:
                        temp_path.rename(dest_path)
                        logger.info(f"Download complete, renamed {temp_path} -> {dest_path}")
                    else:
                        # Incomplete download - delete temp file
                        if temp_path.exists():
                            temp_path.unlink()
                        raise Exception(f"Download incomplete: {downloaded}/{total_size} bytes")
                    
                    return {'path': str(dest_path), 'size': downloaded}
                    
        except asyncio.CancelledError:
            # Ensure temp file is deleted on cancellation
            if temp_path.exists():
                temp_path.unlink()
                logger.info(f"Cancelled: Temp file cleaned up: {temp_path}")
            raise
        except Exception as e:
            # Clean up temp file on any error
            if temp_path.exists():
                temp_path.unlink()
                logger.error(f"Error during download, temp file deleted: {temp_path}")
            raise
    
    # Register routes with the app
    try:
        app = PromptServer.instance.app
        app.router.add_post('/model_linker/analyze', analyze_workflow)
        app.router.add_post('/model_linker/resolve', resolve_models)
        app.router.add_get('/model_linker/models', get_models)
        app.router.add_get('/model_linker/health', health_check)
        app.router.add_post('/model_linker/cache/refresh', refresh_cache)
        app.router.add_post('/model_linker/download', download_model)
        app.router.add_get('/model_linker/download/{download_id}/progress', get_download_progress)
        app.router.add_post('/model_linker/download/{id}/cancel', cancel_download)
        
        _routes_registered = True
        logger.info("✓ Model Linker: API routes registered successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Model Linker: Failed to register routes: {e}", exc_info=True)
        return False


def delayed_registration():
    """
    Background thread that waits for PromptServer to be ready,
    then registers routes. This handles the timing issue in ComfyUI Desktop.
    """
    max_attempts = 30  # Try for up to 30 seconds
    attempt = 0
    
    while attempt < max_attempts and not _routes_registered:
        attempt += 1
        time.sleep(1)
        
        if register_api_routes():
            logger.info(f"Model Linker: Routes registered on attempt {attempt}")
            return
        
        if attempt % 5 == 0:
            logger.debug(f"Model Linker: Waiting for server... (attempt {attempt}/{max_attempts})")
    
    if not _routes_registered:
        logger.warning("Model Linker: Could not register routes after maximum attempts")


# Try immediate registration first
if not register_api_routes():
    # If immediate registration fails, start background thread
    logger.info("Model Linker: Starting delayed registration thread...")
    registration_thread = threading.Thread(target=delayed_registration, daemon=True)
    registration_thread.start()
else:
    logger.info("Model Linker: Immediate registration successful")
