MAX_IMAGE_PIXELS = 40_000_000


def validate_image_dimensions(width: int, height: int) -> None:
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise ValueError("Image dimensions are invalid or exceed the pixel limit")
