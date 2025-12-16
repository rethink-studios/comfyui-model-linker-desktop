# ComfyUI Model Linker - Desktop Edition

**Version 2.1.0** | December 16, 2025

A ComfyUI Desktop-compatible fork that automatically detects missing models in workflows and helps you relink them with intelligent fuzzy matching.

**Based on the work of:**
1. **[@kianxyzw](https://github.com/kianxyzw)** - [Original Model Linker](https://github.com/kianxyzw/comfyui-model-linker) ⭐
2. **[@gontz](https://github.com/gontz)** - [Improved Fork](https://github.com/gontz/comfyui-model-linker) ⭐

![Model Linker Demo](model-linker.png)

## What's New in This Desktop Edition?

This fork adds **ComfyUI Desktop compatibility** with major enhancements:

### Latest Updates (December 16, 2025)
- 🎯 **Smart Multi-Option Selection**: 90-99% confidence matches show 2-3 options with individual resolve buttons
- 📻 **Radio Button Selection**: 70-89% confidence matches let you pick the correct model manually
- 🧠 **Intelligent Token-Based Matching**: Version-aware algorithm (e.g., `wan2.1` vs `wan2.2` are now distinct!)
- 🐛 **Critical Bug Fix**: Fixed false 100% matches caused by version numbers being treated as file extensions
- ✅ **Improved Accuracy**: Correct matches now score 87-94% vs wrong matches at 43-49%

### Core Features
- ✅ **Desktop App Support**: Works seamlessly in ComfyUI Desktop's Electron environment
- 🎯 **Draggable Button**: Movable UI button with position persistence
- 🔧 **Fixed API Routing**: Proper URL handling for Desktop's architecture
- 💾 **Position Memory**: Button position saves across sessions
- 🔍 **Enhanced Logging**: Better debugging support for Desktop environment

## Features

- 🔍 **Automatic Detection**: Scans workflows and identifies all missing models
- 🧠 **Smart Token-Based Matching**: Version-aware fuzzy matching that understands model names (e.g., distinguishes `wan2.1` from `wan2.2`)
- 💯 **Confidence-Based Workflow**: Three tiers of matching confidence
  - 🟢 **100% Perfect Matches**: Auto-resolvable with one click
  - 🟡 **90-99% High Confidence**: Shows 2-3 options, click to resolve your choice
  - ⚪ **70-89% Medium Confidence**: Radio button selection for manual verification
- 🔗 **Flexible Resolution**: One-click resolve or manual selection based on confidence
- ⚡ **Batch Auto-Resolve**: Automatically resolve all 100% confidence matches at once
- 🎨 **Draggable UI**: Movable button that remembers its position
- 💾 **Position Memory**: Button position persists across sessions

## Installation

### For ComfyUI Desktop

1. Navigate to your ComfyUI custom nodes directory:
   ```
   C:\ComfyUIData\custom_nodes\
   ```

2. Clone this repository:
   ```bash
   cd C:\ComfyUIData\custom_nodes
   git clone https://github.com/rethink-studios/comfyui-model-linker.git
   ```

3. Restart ComfyUI Desktop

4. You should see a draggable "🔗 Model Linker" button in the top-right corner

### For Standard ComfyUI

1. Navigate to your ComfyUI custom nodes directory:
   ```
   ComfyUI/custom_nodes/
   ```

2. Clone this repository:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/rethink-studios/comfyui-model-linker.git
   ```

3. Restart ComfyUI

## Usage

### Basic Workflow

1. **Open Model Linker**: Click the "🔗 Model Linker" button in the UI
2. **Review Missing Models**: The dialog shows all missing models organized by confidence level:

   **🟢 100% Perfect Matches** (Green)
   - Exact filename matches after normalization
   - Will be auto-resolved when you click "Auto-Resolve 100% Matches"
   
   **🟡 90-99% High Confidence** (Orange)
   - Shows 2-3 best matching options
   - Each option has its own "Resolve" button
   - Click "Resolve" on the correct model
   - Great for minor filename variations (e.g., `model_v1` vs `model-v1`)
   
   **⚪ 70-89% Medium Confidence** (Gray)
   - Shows 2-3 possible matches with radio buttons
   - Select the correct model using radio buttons
   - Click "Resolve Selected" to apply your choice
   - Manual verification recommended

3. **Resolve Your Choices**: 
   - For 90-99%: Click "Resolve" on the correct option
   - For 70-89%: Select with radio button, then click "Resolve Selected"
   
4. **Auto-Resolve Perfect Matches**: Click "Auto-Resolve 100% Matches" to fix all perfect matches at once

### Dragging the Button

- Click and hold the button to drag it to your preferred position
- Position is automatically saved and persists across sessions
- Quick click (without dragging) opens the Model Linker dialog

## How It Works

### Detection

The Model Linker scans your workflow and identifies:
- Checkpoints
- LoRAs
- VAEs
- ControlNet models
- Text encoders
- And more...

### Fuzzy Matching

Uses **token-based intelligent matching** to find similar models:
- **Exact filename matches** (100% confidence)
- **Version number awareness**: Distinguishes `2.1` from `2.2`, `v1` from `v2`
- **Token-based comparison**: Breaks filenames into meaningful components
- **Weighted scoring**: 70% token similarity + 30% character similarity
- **Normalized comparisons**: Handles `_`, `-`, `.` variations (e.g., `model_name` = `model-name`)
- **Category-aware searching**: Only searches appropriate model types

**Example:**
```
Target: wan2.1_t2v_14B_fp8_scaled.safetensors

❌ Wrong:   wan2.2_fun_control_high_noise... → 49% (different version!)
✅ Correct: Wan2_1-T2V-14B_fp8_e4m3fn...    → 87% (same version & key tokens)
```

### Resolution

When you resolve a model:
1. The workflow is updated with the correct model path
2. The UI immediately reflects the change
3. The updated workflow is ready to run

## Configuration

### Model Paths

Model Linker automatically scans all configured model directories in ComfyUI. To add additional directories:

1. Edit your `extra_model_paths.yaml` file
2. Add your custom model directories
3. Restart ComfyUI

Example:
```yaml
your_models:
  base_path: C:\ComfyUI\models
  checkpoints: checkpoints
  loras: loras
  vae: vae
```

## Troubleshooting

### Button Not Showing

1. Check the browser console (Ctrl+Shift+I) for errors
2. Ensure the extension loaded: Look for "Model Linker: API routes registered successfully!"
3. Try clearing browser cache and restarting ComfyUI

### Models Not Found

1. Verify your model directories are configured in `extra_model_paths.yaml`
2. Check that models are in the correct category folders
3. Ensure ComfyUI can access the directories (permissions)

### Resolution Not Working

1. Open the browser console (Ctrl+Shift+I) to see detailed logs
2. Check for "Updated X model paths in workflow" message
3. Verify the workflow format is compatible (Graph or API format)

## Development

### Project Structure

```
comfyui-model-linker/
├── __init__.py              # Extension entry point
├── core/                    # Python backend
│   ├── __init__.py
│   ├── linker.py           # Main linking logic
│   ├── matcher.py          # Fuzzy matching algorithms
│   ├── scanner.py          # Model directory scanning
│   ├── workflow_analyzer.py # Workflow parsing
│   └── workflow_updater.py  # Workflow modification
└── web/                     # JavaScript frontend
    └── linker.js           # UI and client logic
```

### API Endpoints

- `POST /model_linker/analyze` - Analyze workflow for missing models
- `POST /model_linker/resolve` - Apply model resolutions
- `GET /model_linker/models` - List all available models
- `GET /model_linker/health` - Health check

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Credits

This project builds upon excellent work by:

1. **[@kianxyzw](https://github.com/kianxyzw)** - [Original Model Linker](https://github.com/kianxyzw/comfyui-model-linker)  
   Created the original ComfyUI Model Linker with fuzzy matching

2. **[@gontz](https://github.com/gontz)** - [Enhanced Fork](https://github.com/gontz/comfyui-model-linker)  
   Improved the original with additional features and refinements

3. **[RETHINK Studios](https://github.com/rethink-studios)** - Desktop Edition  
   Adapted for ComfyUI Desktop with draggable UI and bug fixes

Special thanks to both original authors for creating this excellent tool! 🙏

## Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Check the troubleshooting section above
- Enable debug logging in the browser console

---

⭐ If you find this useful, please star the repository!
