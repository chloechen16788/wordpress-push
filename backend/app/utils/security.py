import base64


def encrypt_secret(raw: str) -> str:
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def decrypt_secret(encoded: str) -> str:
    return base64.b64decode(encoded.encode("ascii")).decode("utf-8")

