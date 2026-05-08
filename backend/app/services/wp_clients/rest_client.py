import os
import urllib.parse
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile

from wp_rest_client import WordPressRestClient


class RestPublisherClient:
    def __init__(self, base_url: str, username: str, app_password: str) -> None:
        self.client = WordPressRestClient(
            base_url=base_url,
            username=username,
            app_password=app_password,
        )

    @staticmethod
    def _download_temp_image(url: str) -> Path:
        parsed = urllib.parse.urlparse(url)
        ext = Path(parsed.path).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            ext = ".jpg"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "press-flow-backend/1.0",
                "Accept": "image/*,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        tmp = NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(raw)
        tmp.flush()
        tmp.close()
        return Path(tmp.name)

    def upload_media_from_url(self, image_url: str) -> dict:
        local_path = self._download_temp_image(image_url)
        try:
            mime = WordPressRestClient.guess_mime(local_path)
            resp = self.client.upload_media(file_path=local_path, mime_type=mime)
            return {"id": int(resp["id"]), "source_url": resp.get("source_url")}
        finally:
            try:
                os.unlink(local_path)
            except OSError:
                pass

    def create_post(
        self,
        title: str,
        content: str,
        status: str = "draft",
        featured_media_id: int | None = None,
    ) -> dict:
        payload = {"title": title, "content": content, "status": status}
        if featured_media_id is not None:
            payload["featured_media"] = featured_media_id
        return self.client.create_post(payload)

