"""Glow effects — QGraphicsDropShadowEffect utilities and pulse animation."""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def apply_glow(
    widget: QWidget,
    color: str = "#00FFCC",
    radius: int = 25,
    offset: tuple[int, int] = (0, 0),
) -> QGraphicsDropShadowEffect:
    """Apply a neon glow effect to a widget."""
    effect = QGraphicsDropShadowEffect()
    effect.setOffset(*offset)
    effect.setBlurRadius(radius)
    effect.setColor(QColor(color))
    widget.setGraphicsEffect(effect)
    return effect


def remove_glow(widget: QWidget) -> None:
    """Remove the graphics effect from a widget."""
    widget.setGraphicsEffect(None)


def apply_pulse_glow(
    widget: QWidget,
    color: str = "#00FFCC",
    min_radius: int = 15,
    max_radius: int = 35,
    duration: int = 1500,
) -> "PulseAnimation":
    """Apply an animated pulsing glow to *widget*.

    Returns a :class:`PulseAnimation` that manages the lifecycle.
    """
    effect = apply_glow(widget, color=color, radius=min_radius)
    pulse = PulseAnimation(effect, min_radius, max_radius, duration)
    pulse.start()
    return pulse


class PulseAnimation:
    """Manages a QPropertyAnimation that pulses a drop-shadow blur radius."""

    def __init__(
        self,
        effect: QGraphicsDropShadowEffect,
        min_radius: int = 15,
        max_radius: int = 35,
        duration: int = 1500,
    ) -> None:
        self._effect = effect
        self._anim = QPropertyAnimation(effect, b"blurRadius")
        self._anim.setDuration(duration)
        self._anim.setStartValue(float(min_radius))
        self._anim.setEndValue(float(max_radius))
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.setLoopCount(-1)  # infinite

    # ------------------------------------------------------------------
    def start(self) -> None:
        self._anim.start()

    def stop(self) -> None:
        self._anim.stop()

    def is_running(self) -> bool:
        return self._anim.state() == QPropertyAnimation.State.Running

    @property
    def effect(self) -> QGraphicsDropShadowEffect:
        return self._effect

    @property
    def animation(self) -> QPropertyAnimation:
        return self._anim
