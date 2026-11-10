"""
Rebuild a table grid from OCR text boxes.

This is the algorithm from the Colab prototype (research/colab_prototype.py),
cleaned up and without the TensorFlow dependency:

1. Every text box is stretched to the full image width  -> a "row candidate",
   and to the full image height                          -> a "column candidate".
2. Non-max suppression merges overlapping candidates, leaving one band per
   real row and one per real column.
3. Bands are sorted top->bottom / left->right; each text box is put into the
   cell (row band x column band) it overlaps most.
"""

from dataclasses import dataclass

import numpy as np

BAND_IOU_THRESHOLD = 0.1   # NMS threshold used in the prototype
CELL_IOU_THRESHOLD = 0.1   # min overlap for a text box to belong to a cell


@dataclass
class TextBox:
    x1: float
    y1: float
    x2: float
    y2: float
    text: str
    score: float = 1.0

    @classmethod
    def from_polygon(cls, points, text, score=1.0):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return cls(min(xs), min(ys), max(xs), max(ys), text, float(score))

    @property
    def rect(self):
        return (self.x1, self.y1, self.x2, self.y2)


def iou(a, b):
    """Intersection over union of two (x1, y1, x2, y2) rectangles."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / float(area_a + area_b - inter)


def non_max_suppression(rects, scores, iou_threshold):
    """Greedy NMS (same behaviour as tf.image.non_max_suppression). Returns kept indices."""
    order = list(np.argsort(-np.asarray(scores, dtype=float), kind="stable"))
    keep = []
    while order:
        best = order.pop(0)
        keep.append(best)
        order = [i for i in order if iou(rects[best], rects[i]) <= iou_threshold]
    return keep


def build_grid(boxes, width, height):
    """Return the table as a list of rows (lists of strings)."""
    boxes = [b for b in boxes if b.text and b.text.strip()]
    if not boxes:
        return []

    scores = [b.score for b in boxes]
    row_bands = [(0, b.y1, width, b.y2) for b in boxes]
    col_bands = [(b.x1, 0, b.x2, height) for b in boxes]

    rows = non_max_suppression(row_bands, scores, BAND_IOU_THRESHOLD)
    cols = non_max_suppression(col_bands, scores, BAND_IOU_THRESHOLD)
    rows.sort(key=lambda i: row_bands[i][1])   # top -> bottom
    cols.sort(key=lambda i: col_bands[i][0])   # left -> right

    grid = [["" for _ in cols] for _ in rows]
    for box in sorted(boxes, key=lambda b: (b.y1, b.x1)):
        best, best_iou = None, CELL_IOU_THRESHOLD
        for r, ri in enumerate(rows):
            for c, ci in enumerate(cols):
                cell = (col_bands[ci][0], row_bands[ri][1], col_bands[ci][2], row_bands[ri][3])
                score = iou(cell, box.rect)
                if score > best_iou:
                    best, best_iou = (r, c), score
        if best is None:
            continue
        r, c = best
        grid[r][c] = f"{grid[r][c]} {box.text}".strip() if grid[r][c] else box.text.strip()

    return _drop_empty(grid)


def _drop_empty(grid):
    grid = [row for row in grid if any(cell for cell in row)]
    if not grid:
        return []
    keep_cols = [c for c in range(len(grid[0])) if any(row[c] for row in grid)]
    return [[row[c] for c in keep_cols] for row in grid]
