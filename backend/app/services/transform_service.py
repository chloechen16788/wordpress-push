import json
from pathlib import Path
from typing import Any

from amp_to_wp_input import build_article_content


def normalize_content(raw_record: dict[str, Any]) -> dict[str, Any]:
    content_html, _ = build_article_content(
        raw_record,
        append_image=False,
        normalize_amp_images=True,
    )
    return {
        "nm_transmission_id": raw_record.get("nm_transmission_id"),
        "title": raw_record.get("title"),
        "content_html": content_html,
        "image_url": raw_record.get("image_url"),
        "raw_json": json.dumps(raw_record, ensure_ascii=False),
    }


def ensure_media_workspace(base_dir: Path) -> dict[str, Path]:
    featured_dir = base_dir / "temp" / "amp_featured"
    inline_dir = base_dir / "temp" / "amp_inline"
    featured_dir.mkdir(parents=True, exist_ok=True)
    inline_dir.mkdir(parents=True, exist_ok=True)
    return {"featured_dir": featured_dir, "inline_dir": inline_dir}

