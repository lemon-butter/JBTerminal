# JBTerminal

A native desktop terminal emulator designed for AI CLI tools (Claude Code). Built with PyQt6, featuring a neon glow design system and full Korean IME support.

## Features

- **Native terminal emulator** -- pyte-based rendering with QPainter, no xterm.js dependency
- **PTY management** -- full pseudo-terminal support with fork/exec, SIGWINCH resize
- **Split panes** -- binary-tree based horizontal/vertical splits with drag-to-resize dividers
- **Multi-tab support** -- create, close, rename, and drag-reorder tabs
- **Workspace management** -- sidebar with project workspaces, layout save/restore
- **Neon glow design system** -- custom QSS + QPainter effects, 5 built-in theme presets (Neon Dark, Neon Light, Dracula, Nord, Tokyo Night)
- **Claude Code integration** -- PTY output state detection (idle/thinking/tool_use/done/error/waiting), usage monitoring (CTX/5H/7D), session file watching
- **macOS notifications** -- alerts when tasks complete in background workspaces
- **Korean IME composition** -- full input method support for CJK text entry
- **In-terminal search** -- Cmd+F to search scrollback and screen buffer
- **Settings UI** -- font picker, theme picker, terminal configuration
- **Keyboard shortcuts** -- Ctrl+T (new tab), Ctrl+W (close tab), Ctrl+D (split), Ctrl+B (toggle sidebar), Ctrl+, (settings)

## Screenshots

<!-- TODO: Add screenshots -->

## Installation

**Requirements:** Python 3.9+, macOS (for pyobjc notifications)

```bash
# Clone the repository
git clone https://github.com/your-org/JBTerminal.git
cd JBTerminal

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python src/main.py
```

## Development Setup

```bash
# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_pane_tree.py tests/test_workspace.py -v
python -m pytest tests/test_integration.py -v
```

## Architecture

```
src/
  main.py                    # Entry point
  app.py                     # QApplication setup, theme loading, app icon
  models/
    enums.py                 # PaneState, SplitDirection enums
    pane_tree.py             # Binary tree for split pane layout
    workspace.py             # Workspace and tab state model
  terminal/
    pty_manager.py           # PTY process pool (fork/exec, reader threads)
    terminal_widget.py       # pyte-backed terminal renderer (QPainter)
    terminal_config.py       # Per-terminal settings (font, spacing, scrollback)
  ui/
    main_window.py           # QMainWindow -- assembles all components
    sidebar.py               # Workspace list sidebar
    tab_bar.py               # Terminal tab bar
    split_pane.py            # Binary-tree split pane container
    pane_view.py             # Individual pane (header + terminal)
    pane_divider.py          # Draggable split resize handle
  theme/
    tokens.py                # Design tokens (colors, spacing)
    theme_manager.py         # Theme loading, switching, QSS generation
    effects.py               # QPainter glow and shadow effects
    presets/                  # Theme preset definitions
  status/
    status_bar.py            # Bottom status bar (usage gauges)
    usage_monitor.py         # Claude Code usage tracking (CTX/5H/7D)
    session_watcher.py       # JSONL session file monitoring
    state_detector.py        # PTY output state classification
  settings/
    config.py                # JSON config persistence + layout serialization
    settings_dialog.py       # Settings dialog UI
    font_picker.py           # Font selection widget
    theme_picker.py          # Theme selection widget
  notifications/
    notifier.py              # macOS system notifications
    hooks_handler.py         # Claude Code hooks integration
  widgets/
    neon_button.py           # Custom glow button
    neon_frame.py            # Custom glow frame container
    neon_progress.py         # Neon progress bar
    neon_tab_bar.py          # Neon-styled tab bar widget
  resources/
    icon.py                  # Programmatic app icon (QPainter)
tests/
  test_pane_tree.py          # Pane tree unit tests
  test_workspace.py          # Workspace model unit tests
  test_pty_manager.py        # PTY manager tests
  test_status_features.py    # Status/state detection tests
  test_integration.py        # End-to-end integration tests
```

## Credits

- **PyQt6** -- Qt bindings for Python
- **pyte** -- VTXXX-compatible terminal emulator library
- **pyobjc** -- macOS Cocoa bridge for native notifications
- Inspired by the UX design of [Claude Code](https://claude.ai) terminal interfaces
