from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from numpy.typing import NDArray

Image = NDArray[np.uint8]
"""An RGB image of shape (height, width, 3)."""


@dataclass(frozen=True, slots=True)
class Frame:
    image: Image
    at: datetime

    @property
    def width(self) -> int:
        return int(self.image.shape[1])

    @property
    def height(self) -> int:
        return int(self.image.shape[0])
