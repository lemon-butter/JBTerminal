"""Programmatic app icon -- neon terminal icon using QPainter."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)


def create_app_icon(size: int = 256) -> QIcon:
    """Create a neon-styled terminal icon programmatically.

    The icon features:
    - Dark rounded-rect background
    - Neon-green terminal prompt glow
    - Cursor block
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = int(size * 0.08)
    body = QRect(margin, margin, size - 2 * margin, size - 2 * margin)

    # -- Background with subtle gradient --
    bg_grad = QLinearGradient(0, 0, 0, size)
    bg_grad.setColorAt(0.0, QColor("#0e0e24"))
    bg_grad.setColorAt(1.0, QColor("#08081a"))
    painter.setBrush(bg_grad)
    painter.setPen(Qt.PenStyle.NoPen)
    radius = int(size * 0.18)
    painter.drawRoundedRect(body, radius, radius)

    # -- Border glow --
    border_pen = QPen(QColor(0, 255, 204, 100))
    border_pen.setWidth(max(2, int(size * 0.012)))
    painter.setPen(border_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(body, radius, radius)

    # -- Title bar dots (red/yellow/green) --
    dot_y = margin + int(size * 0.10)
    dot_r = max(3, int(size * 0.028))
    dot_spacing = int(size * 0.07)
    dot_start_x = margin + int(size * 0.10)
    for i, color in enumerate(["#FF5F57", "#FFBD2E", "#28CA42"]):
        cx = dot_start_x + i * dot_spacing
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawEllipse(QPoint(cx, dot_y), dot_r, dot_r)

    # -- Terminal prompt text --
    accent = QColor("#00FFCC")
    glow_color = QColor(0, 255, 204, 60)

    # Prompt line area
    prompt_y = margin + int(size * 0.35)
    prompt_x = margin + int(size * 0.10)
    line_h = int(size * 0.10)

    # Draw glow behind the prompt character
    glow_grad = QRadialGradient(prompt_x + int(size * 0.04), prompt_y + line_h // 2, int(size * 0.15))
    glow_grad.setColorAt(0.0, QColor(0, 255, 204, 50))
    glow_grad.setColorAt(1.0, QColor(0, 255, 204, 0))
    painter.setBrush(glow_grad)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(
        QPoint(prompt_x + int(size * 0.04), prompt_y + line_h // 2),
        int(size * 0.15),
        int(size * 0.12),
    )

    # Draw ">" prompt character
    pen = QPen(accent)
    pen.setWidth(max(2, int(size * 0.022)))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)

    chevron_x = prompt_x
    chevron_mid_x = prompt_x + int(size * 0.06)
    chevron_top_y = prompt_y
    chevron_mid_y = prompt_y + line_h // 2
    chevron_bot_y = prompt_y + line_h
    painter.drawLine(chevron_x, chevron_top_y, chevron_mid_x, chevron_mid_y)
    painter.drawLine(chevron_mid_x, chevron_mid_y, chevron_x, chevron_bot_y)

    # Draw cursor block
    cursor_x = prompt_x + int(size * 0.12)
    cursor_w = int(size * 0.06)
    cursor_h = line_h
    cursor_color = QColor(0, 255, 204, 180)
    painter.setBrush(cursor_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRect(cursor_x, prompt_y, cursor_w, cursor_h)

    # -- Second line: dim text placeholder --
    line2_y = prompt_y + int(size * 0.18)
    dim_color = QColor(255, 255, 255, 60)
    painter.setBrush(dim_color)
    for i in range(4):
        bx = prompt_x + i * int(size * 0.09)
        bw = int(size * 0.06)
        bh = int(size * 0.04)
        painter.drawRoundedRect(bx, line2_y, bw, bh, 2, 2)

    # -- Third line: another dim placeholder --
    line3_y = line2_y + int(size * 0.12)
    for i in range(3):
        bx = prompt_x + i * int(size * 0.10)
        bw = int(size * 0.07)
        bh = int(size * 0.04)
        painter.drawRoundedRect(bx, line3_y, bw, bh, 2, 2)

    painter.end()

    icon = QIcon()
    icon.addPixmap(pixmap)
    # Also generate a smaller variant for better clarity at small sizes
    if size > 64:
        small = create_app_icon(64)
        for pm_size in [16, 32, 48, 64]:
            icon.addPixmap(small.pixmap(pm_size, pm_size))
    return icon
