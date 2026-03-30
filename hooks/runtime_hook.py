"""PyInstaller runtime hook — set QT_PLUGIN_PATH for bundled .app.

This runs BEFORE the main script, so Qt can find its plugins.
"""
import os
import sys

if getattr(sys, 'frozen', False):
    bundle_dir = os.path.dirname(os.path.abspath(sys.executable))

    # Try multiple known locations
    candidates = [
        os.path.join(bundle_dir, '..', 'Frameworks', 'PyQt6', 'Qt6', 'plugins'),
        os.path.join(bundle_dir, '..', 'Resources', 'PyQt6', 'Qt6', 'plugins'),
        os.path.join(bundle_dir, 'PyQt6', 'Qt6', 'plugins'),
    ]

    for c in candidates:
        real = os.path.realpath(c)
        if os.path.isdir(real):
            os.environ['QT_PLUGIN_PATH'] = real
            break

    # Also debug print
    print(f"[runtime_hook] frozen={getattr(sys, 'frozen', False)}")
    print(f"[runtime_hook] exe={sys.executable}")
    print(f"[runtime_hook] QT_PLUGIN_PATH={os.environ.get('QT_PLUGIN_PATH', 'NOT SET')}")
