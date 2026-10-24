"""Public images contain freshly encoded pixels, never original metadata or frames."""

import io
import warnings
from collections.abc import Buffer
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.modules.identity.security import AuthError

MAX_IMAGE_PIXELS = 16_000_000
FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


class _BoundedOutput(io.BytesIO):
    def __init__(self, limit: int):
        super().__init__()
        self.limit = limit

    def write(self, value: Buffer, /) -> int:
        if self.tell() + memoryview(value).nbytes > self.limit:
            raise ValueError("public_image_too_large")
        return super().write(value)


def sanitize_image(source: BinaryIO, media_type: str, max_bytes: int) -> BinaryIO:
    output = _BoundedOutput(max_bytes)
    try:
        if media_type not in FORMATS:
            raise ValueError
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source, formats=[FORMATS[media_type]]) as image:
                if (
                    image.width * image.height > MAX_IMAGE_PIXELS
                    or getattr(image, "n_frames", 1) != 1
                ):
                    raise ValueError
                image.load()
                oriented = ImageOps.exif_transpose(image)
                mode = "RGB" if media_type == "image/jpeg" else "RGBA"
                with Image.new(mode, oriented.size) as canvas:
                    canvas.paste(oriented.convert(mode))
                    canvas.save(
                        output, format=FORMATS[media_type], exif=b"", icc_profile=None, xmp=b""
                    )
        output.seek(0)
        return output
    except (
        OSError,
        ValueError,
        SyntaxError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        output.close()
        raise AuthError("asset_image_invalid", 422) from None
