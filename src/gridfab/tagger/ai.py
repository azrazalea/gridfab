"""AI-assisted sprite naming via Claude Code CLI."""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image


class AIAssistant:
    """Generates sprite names and descriptions using Claude Code CLI."""

    MODEL_MAP = {
        "haiku": "claude-haiku-4-5-20251001",
        "sonnet": "claude-sonnet-4-5-20250929",
        "opus": "claude-opus-4-5-20251101",
    }

    def __init__(self, model: str = "haiku"):
        self.model = self.MODEL_MAP.get(model, self.MODEL_MAP["haiku"])
        self.model_name = model
        self.temp_dir = Path(tempfile.mkdtemp(prefix="tileset_tagger_"))
        self.available = self._check_available()

    def _check_available(self) -> bool:
        """Check if claude CLI is installed."""
        return shutil.which("claude") is not None

    def generate(self, tags: list[str], tile_img: Image.Image,
                 context_img: Image.Image | None = None,
                 row: int = 0, col: int = 0,
                 tiles_x: int = 1, tiles_y: int = 1,
                 recent_context: list[dict] | None = None,
                 existing_name: str | None = None,
                 existing_desc: str | None = None) -> dict:
        """Generate name + description from tags and tile image via Claude Code."""

        if not self.available or not tags:
            return self._fallback(tags, existing_name, existing_desc)

        # Upscale images so the LLM can actually see 32px pixel art
        # Nearest-neighbor preserves the crisp pixel look
        TILE_SCALE = 8  # 32px -> 256px
        CONTEXT_SCALE = 4  # context region -> reasonable size

        tile_upscaled = tile_img.resize(
            (tile_img.width * TILE_SCALE, tile_img.height * TILE_SCALE),
            Image.NEAREST,
        )
        tile_path = self.temp_dir / "current_tile.png"
        tile_upscaled.save(tile_path)

        context_ref = ""
        if context_img is not None:
            ctx_upscaled = context_img.resize(
                (context_img.width * CONTEXT_SCALE, context_img.height * CONTEXT_SCALE),
                Image.NEAREST,
            )
            ctx_path = self.temp_dir / "context.png"
            ctx_upscaled.save(ctx_path)
            context_ref = f"\nAlso read the file context.png to see surrounding tiles for additional understanding."

        tags_str = ", ".join(tags)
        size_str = f"{tiles_x}x{tiles_y} tiles" if tiles_x > 1 or tiles_y > 1 else "single tile"

        # Build recent context section
        context_section = ""
        if recent_context:
            lines = []
            for s in recent_context[-6:]:  # Last 6 for prompt brevity
                lines.append(f"  row {s['row']}, col {s['col']}: \"{s['name']}\" "
                             f"tags=[{', '.join(s.get('tags', []))}] "
                             f"— {s.get('description', '')}")
            context_section = "\n\nRecently tagged nearby sprites (for naming consistency):\n" + "\n".join(lines)

        # Existing name/description hints
        name_hint = ""
        if existing_name:
            name_hint = f"\nThe user has named this sprite: \"{existing_name}\". Keep this name unless it is clearly wrong for the tags. Only make minor adjustments like fixing formatting to snake_case."
        desc_hint = ""
        if existing_desc:
            desc_hint = f"\nThe user's draft description is: \"{existing_desc}\". Expand, refine, or complete it. Keep the user's intent."

        prompt = f"""You are naming a pixel art sprite for a game tileset index.

User-applied tags: {tags_str}
Sprite size: {size_str} (each tile is 32x32 pixels, images are upscaled for visibility)
Location: row {row}, col {col}{name_hint}{desc_hint}{context_section}

Read the file current_tile.png to see the sprite.{context_ref}

Respond with ONLY this JSON on a single line (no markdown, no fences, no explanation):
{{"name": "snake_case_name", "description": "One sentence description of what this sprite depicts"}}

Rules:
- name: snake_case, concise, 2-4 words max. Be consistent with the naming style of recently tagged sprites.
- description: One brief sentence
- The user tags are the primary signal for what this is; use the image for extra detail"""

        try:
            result = subprocess.run(
                ["claude", "-p", prompt,
                 "--model", self.model,
                 "--output-format", "json",
                 "--allowedTools", "Read"],
                cwd=self.temp_dir,
                capture_output=True, text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            print("  AI generation timed out")
            return self._fallback(tags, existing_name, existing_desc)
        except Exception as e:
            print(f"  AI subprocess error: {e}")
            return self._fallback(tags, existing_name, existing_desc)

        if result.returncode != 0:
            print(f"  AI returned non-zero exit code: {result.returncode}")
            if result.stderr:
                print(f"  stderr: {result.stderr[:200]}")
            return self._fallback(tags, existing_name, existing_desc)

        # Parse Claude Code's JSON wrapper
        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"  AI outer JSON parse failed. stdout starts with: {result.stdout[:200]}")
            return self._fallback(tags, existing_name, existing_desc)

        # Extract the text content from Claude Code's response
        # Claude Code --output-format json can return:
        #   {"result": "..."} or {"content": [{"text": "..."}]} or other structures
        text = ""
        if isinstance(response, dict):
            if "result" in response and response["result"]:
                text = response["result"]
            elif "content" in response:
                # Content blocks format
                content = response["content"]
                if isinstance(content, list):
                    text = " ".join(
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
                elif isinstance(content, str):
                    text = content
            # Try other common fields
            if not text:
                for key in ("text", "message", "output"):
                    if key in response and isinstance(response[key], str):
                        text = response[key]
                        break

        if not text:
            print(f"  AI response had no extractable text. Keys: {list(response.keys()) if isinstance(response, dict) else type(response)}")
            return self._fallback(tags, existing_name, existing_desc)

        # Extract JSON object from the text (may have markdown fences, preamble, etc.)
        text = text.strip()

        # Try direct parse first
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "name" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

        # Strip markdown fences
        cleaned = text
        if "```" in cleaned:
            # Extract content between fences
            fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', cleaned, re.DOTALL)
            if fence_match:
                cleaned = fence_match.group(1).strip()

        # Try parsing cleaned version
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "name" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

        # Last resort: find JSON object in text with regex
        obj_match = re.search(r'\{[^{}]*"name"\s*:\s*"[^"]*"[^{}]*\}', text)
        if obj_match:
            try:
                parsed = json.loads(obj_match.group(0))
                if "name" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass

        print(f"  AI response text could not be parsed as JSON: {text[:200]}")
        return self._fallback(tags, existing_name, existing_desc)

    def _fallback(self, tags: list[str], existing_name: str | None = None,
                  existing_desc: str | None = None) -> dict:
        """Generate a simple name/description from tags alone."""
        if not tags and not existing_name:
            return {"name": "unnamed_sprite", "description": existing_desc or "Untagged sprite"}
        name = existing_name or "_".join(tags[:4])
        desc = existing_desc or ("A " + " ".join(tags) + " sprite" if tags else "")
        return {"name": name, "description": desc}

    def cleanup(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
