#!/usr/bin/env python
import argparse
import os
import datetime
import torch
from diffusers import StableDiffusionPipeline, LoRA

BASE_DIR = r"C:\Project\Artwork\AI_Models\stable-diffusion-v2-1-base"
LORA_DIR = r"C:\Project\Artwork\AI_Models\pixelart-lora"
OUT_DIR = r"C:\Project\Artwork\Sprites\pixelart-lora"

def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S-%f")[:-3]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="Prompt text")
    parser.add_argument("--name", help="Optional custom filename")
    parser.add_argument("--resolution", type=int, default=64,
                        help="Any pixel dimension (e.g., 64, 128, 256)")
    args = parser.parse_args()

    pipe = StableDiffusionPipeline.from_pretrained(
        BASE_DIR,
        torch_dtype=torch.float16
    ).to("cuda")
    lora = LoRA.from_pretrained(LORA_DIR)
    pipe.load_lora_weights(lora)
    res_dir = os.path.join(OUT_DIR, str(args.resolution))
    os.makedirs(res_dir, exist_ok=True)
    filename = args.name or timestamp()
    out_path = os.path.join(res_dir, f"{filename}.png")
    image = pipe(
        prompt=args.prompt,
        num_inference_steps=25,
        guidance_scale=7.5,
        output_type="pil"
    ).images[0]
    image.save(out_path)
    print(f"Sprite saved to {out_path}")

if __name__ == "__main__":
    main()
