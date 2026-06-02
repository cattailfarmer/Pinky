# Pixel‑Art Generation Guide

## What
This document describes how to generate pixel‑style sprites for game assets using a Stable Diffusion 2.1 base model with a dedicated LoRA.  The workflow is fully local, supports arbitrary resolutions, and runs on an RTX 5090 with a 16 GB budget.

## Pre‑requisites
| Component | Version | Notes |
|-----------|---------|-------|
| Python | ≥ 3.10 | Python 3.10 used in the provided script |
| PyTorch | 2.3.0+cu121 | Built for CUDA 12.1, required by Diffusers |
| Diffusers | 0.13.x | Handles SD‑2.1 pipeline and LoRA loading |
| Git LFS | – | Needed for downloading the large checkpoints |
| NVIDIA GPU | RTX 5090 | 32 GB VRAM, but script limits to 16 GB per request |

## Setup
1. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. **Install dependencies**:
   ```bash
   pip install torch==2.3.0+cu121 --extra-index-url https://download.pytorch.org/whl/cu121
   pip install diffusers==0.13.2 transformers==4.36.2 accelerate
   ```
3. **Download checkpoints** (use the fine‑grained token if needed):
   ```powershell
   git lfs clone https://huggingface.co/CompVis/stable-diffusion-v2-1-base \
     "C:\\Project\\Artwork\\AI_Models\\stable-diffusion-v2-1-base"
   git lfs clone https://huggingface.co/pczh/pixelart-lora \
     "C:\\Project\\Artwork\\AI_Models\\pixelart-lora"
   ```

## Usage
```bash
python scripts/gen_sprite.py --prompt "red fox" \
    --resolution 128 \
    --name fox_red_001
```
The output will be written to:
```
C:\Project\Artwork\Sprites\pixelart-lora\128\fox_red_001.png
```
If `--name` is omitted, a timestamp‑based name will be used.

## OpenCode Integration
OpenCode now exposes a `sprite` chat command that delegates to the script above.  A typical invocation in chat would be:

```text
sprite "blue wizard" "wizard_blue_001" 128
```
The response will contain a Markdown image link pointing to the generated PNG.

## Folder Layout
```
C:\Project\Artwork\AI_Models\
├─ stable-diffusion-v2-1-base\
└─ pixelart-lora\
C:\Project\Artwork\Sprites\pixelart-lora\<resolution>\<filename>.png
```

## Licensing
Both the SD‑2.1 base and the pixel‑art LoRA are released under public‑domain / CC‑0 terms.  Generated images inherit the same permissive license.

---

*This guide is auto‑generated to assist developers integrating the sprite generator.*
