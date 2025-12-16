# Changelog

All notable changes to ComfyUI Model Linker - Desktop Edition will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2025-12-16

### Added - Download Functionality
- **Direct Model Downloads**: Download missing models from any URL with progress tracking
- **Real-Time Progress Bars**: Visual progress showing percentage, MB downloaded/total
- **Cancel Downloads**: Stop downloads mid-transfer with "Cancel" button
- **Search Integration**: Quick search buttons for CivitAI and HuggingFace
- **URL Input Field**: Paste any direct download URL
- **Progress Polling**: Backend polls download progress every 500ms
- **Auto-Installation**: Downloads automatically place in correct model directories

### Added - Safety Features
- **Temporary File Protection**: Downloads to `.tmp` files first
- **Atomic Rename**: Only renames to final name when 100% complete
- **Partial File Cleanup**: Cancelled/failed downloads cleaned up instantly
- **No Corrupted Models**: ComfyUI never sees incomplete downloads
- **Size Verification**: Validates downloaded size matches expected size

### Added - API Endpoints
- `POST /model_linker/download` - Start model download
- `GET /model_linker/download/{id}/progress` - Get download progress
- `POST /model_linker/download/{id}/cancel` - Cancel active download

### Improved
- Enhanced UI for "No Good Matches" section (< 75% confidence)
- Better visual hierarchy with download controls
- More intuitive workflow for finding and installing missing models
- New demo video showcasing v2.2.0 features (18 MB, down from 78 MB)

### Fixed
- **CRITICAL**: Prevented partial downloads from being detected as valid models
- Downloads now use `.tmp` extension during transfer
- Clean error handling for download failures

## [2.1.0] - 2025-12-16

### Added
- **Multi-Option Selection**: 90-99% confidence matches now show 2-3 options with individual "Resolve" buttons
- **Radio Button Selection**: 70-89% confidence matches display with radio buttons for manual selection
- **Smart Token-Based Matching**: Version-aware fuzzy matching algorithm that understands model naming conventions
- **Confidence-Based Workflow**: Three-tier system (100% auto-resolve, 90-99% multi-option, 70-89% manual selection)

### Fixed
- **CRITICAL**: Fixed `os.path.splitext()` bug that treated version numbers as file extensions
  - Previously: `wan2.1_t2v_14B.safetensors` → split to `wan2` + `.1_t2v_14B.safetensors`
  - Now: Correctly handles version numbers in filenames
- Wrong matches that previously scored 100% now correctly score 43-49%
- Correct matches that previously scored 20% now correctly score 87-94%

### Changed
- Matching algorithm now uses 70% token similarity + 30% character similarity weighting
- Improved tokenization to preserve version numbers and key identifiers
- Enhanced UI with color-coded confidence levels (green, orange, gray)

### Improved
- Version number distinction (e.g., `2.1` vs `2.2`, `v1` vs `v2`)
- Better handling of special characters (`_`, `-`, `.`) in filenames
- More accurate model matching overall

## [2.0.0] - 2025-12-15

### Added
- Initial Desktop Edition fork from original Model Linker
- ComfyUI Desktop (Electron) compatibility
- Draggable UI button with position persistence
- Fixed API routing for Desktop architecture
- Enhanced logging and debugging support
- Position memory using localStorage

### Fixed
- widget_index handling for 0-index values
- Workflow update mechanism using `app.graph.configure()`
- API URL handling for Electron environment (`api.api_base` support)

### Changed
- Adapted JavaScript imports for Desktop web root structure
- Modified backend route registration with delayed setup mechanism
- Updated API endpoints to work with Desktop's architecture

## Credits

Based on excellent work by:
- [@kianxyzw](https://github.com/kianxyzw) - Original Model Linker
- [@gontz](https://github.com/gontz) - Improved Fork
- [RETHINK Studios](https://github.com/rethink-studios) - Desktop Edition

---

**[Unreleased]**: https://github.com/rethink-studios/comfyui-model-linker-desktop/compare/v2.1.0...HEAD  
**[2.1.0]**: https://github.com/rethink-studios/comfyui-model-linker-desktop/compare/v2.0.0...v2.1.0  
**[2.0.0]**: https://github.com/rethink-studios/comfyui-model-linker-desktop/releases/tag/v2.0.0

