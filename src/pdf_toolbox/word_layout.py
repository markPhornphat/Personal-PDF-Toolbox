"""Word placement calculations, in points; no Office dependency."""

from dataclasses import dataclass
import math
import re

MM = 72 / 25.4


@dataclass(frozen=True)
class PlacementSettings:
    horizontal: str = "Center"
    vertical: str = "Bottom"
    scale: float = 100
    safety_mm: float = 5
    dpi: int = 300
    format: str = "JPEG"
    quality: int = 95

    def __post_init__(self):
        if (
            self.horizontal not in {"Left", "Center", "Right"}
            or self.vertical not in {"Top", "Center", "Bottom"}
            or not math.isfinite(self.scale)
            or not 1 <= self.scale <= 200
            or not math.isfinite(self.safety_mm)
            or not 0 <= self.safety_mm <= 50
            or self.dpi not in {150, 200, 300, 600}
            or self.format not in {"JPEG", "PNG"}
            or not 1 <= self.quality <= 100
        ):
            raise ValueError("Choose valid image placement settings.")


@dataclass(frozen=True)
class Layout:
    width: float
    height: float
    left: float
    top: float
    right: float
    bottom: float


@dataclass(frozen=True)
class Rectangle:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height


def fit_image(
    layout: Layout, width: float, height: float, settings: PlacementSettings
) -> Rectangle:
    margin = settings.safety_mm * MM
    left, top = layout.left + margin, layout.top + margin
    available_w = layout.right - margin - left
    available_h = layout.bottom - margin - top
    if (
        not all(math.isfinite(v) for v in (width, height, available_w, available_h))
        or min(width, height, available_w, available_h) <= 0
    ):
        raise ValueError("No safe image area remains. Reduce the additional safety margin.")
    scale = min(available_w / width, available_h / height) * min(settings.scale / 100, 1)
    w, h = width * scale, height * scale
    x = left + (available_w - w) * {"Left": 0, "Center": 0.5, "Right": 1}[settings.horizontal]
    y = top + (available_h - h) * {"Top": 0, "Center": 0.5, "Bottom": 1}[settings.vertical]
    return Rectangle(x, y, w, h)


def natural_key(value):
    return [
        int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", str(value))
    ]
