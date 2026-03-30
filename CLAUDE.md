# JBTerminal — Orchestration Document

AI CLI 도구(Claude Code)를 위한 네이티브 데스크톱 터미널. PyQt6 기반, 네온 글로우 디자인.

## Project Overview

JBTerminal은 한글 IME 조합 입력이 완벽히 동작하는 네이티브 터미널 에뮬레이터를 내장한 GUI 앱이다.
clabs-tauri의 UX/디자인을 참고하되, xterm.js 대신 네이티브 터미널 위젯을 사용하고,
PyQt6의 QSS 한계를 QPainter/QGraphicsEffect로 보완하여 네온 글로우 디자인을 구현한다.

---

## Team Structure & Responsibilities

### Team A — Core Terminal (`core-terminal`)
> PTY 프로세스 관리, 터미널 위젯 통합, 입출력 파이프라인

**담당 영역:**
- PTY 스폰/관리 (pty 모듈 — `subprocess` + `pty` or `pyte`)
- 터미널 에뮬레이터 위젯 (QTermWidget 또는 fallback: pyte + custom QWidget)
- 키 입력 → PTY 쓰기, PTY 출력 → 화면 렌더링
- 터미널 리사이즈 (SIGWINCH)
- 한글 IME 조합 입력 검증
- 줄간격(line spacing) 커스터마이징

**핵심 파일:**
```
src/terminal/pty_manager.py      # PTY 프로세스 풀 관리
src/terminal/terminal_widget.py  # 터미널 에뮬레이터 위젯
src/terminal/terminal_config.py  # 터미널 설정 (폰트, 줄간격 등)
```

### Team B — UI Layout (`ui-layout`)
> 사이드바, 탭, 스플릿 뷰, 드래그 앤 드롭 — 전체 레이아웃 구조

**담당 영역:**
- 메인 윈도우 레이아웃 (사이드바 + 작업 영역)
- 사이드바: 워크스페이스 리스트 (추가/삭제/rename/정렬)
- 탭 바: 멀티 터미널 탭 (추가/삭제/rename/드래그 재배치)
- 스플릿 뷰: 바이너리 트리 기반 상하/좌우 분할
  - `PaneNode = PaneLeaf | PaneSplit` 구조
  - 분할 비율 드래그 조절
  - 탭 → 스플릿 영역 간 드래그 앤 드롭 이동
- 워크스페이스별 탭/스플릿 상태 저장/복원

**핵심 파일:**
```
src/ui/main_window.py            # QMainWindow, 전체 레이아웃 조립
src/ui/sidebar.py                # 워크스페이스 리스트 위젯
src/ui/tab_bar.py                # 터미널 탭 바
src/ui/split_pane.py             # 바이너리 트리 스플릿 뷰 컨테이너
src/ui/pane_view.py              # 개별 페인 (헤더 + 터미널)
src/ui/pane_divider.py           # 스플릿 리사이즈 핸들
src/models/pane_tree.py          # PaneNode 바이너리 트리 자료구조
src/models/workspace.py          # 워크스페이스/탭 상태 모델
```

### Team C — Design System (`design-system`)
> 네온 글로우 테마, 커스텀 위젯, QSS, QPainter 이펙트

**담당 영역:**
- 네온 글로우 디자인 시스템 (아래 Design Spec 참조)
- 글로벌 QSS 테마 시트
- 커스텀 위젯: 글로우 버튼, 글로우 프레임, 프로그레스 바
- QPainter 기반 글로우 이펙트 (QSS box-shadow 없으므로)
- QGraphicsDropShadowEffect 유틸리티
- 테마 프리셋 시스템 (Dark, Light, 커스텀)
- JetBrains/Terminal.app 테마 임포트
- 아이콘 시스템

**핵심 파일:**
```
src/theme/tokens.py              # 디자인 토큰 (색상, 간격, 반경 등)
src/theme/neon_theme.qss         # 글로벌 QSS 스타일시트
src/theme/theme_manager.py       # 테마 로드/전환/프리셋 관리
src/theme/effects.py             # QPainter 글로우, DropShadow 유틸
src/theme/presets/               # 테마 프리셋 디렉토리
  default_dark.py
  default_light.py
src/widgets/neon_button.py       # 글로우 버튼 커스텀 위젯
src/widgets/neon_frame.py        # 글로우 프레임 컨테이너
src/widgets/neon_progress.py     # 네온 프로그레스 바
src/widgets/neon_tab_bar.py      # 네온 탭 바 위젯
```

### Team D — Status & Features (`status-features`)
> 상태 모니터링, 알림, 설정 UI

**담당 영역:**
- 하단 상태바 (CTX / 5H / 7D 사용량 표시)
- Claude Code 상태 감지 (PTY 출력 파싱 또는 Hooks/Statusline JSON)
- 워크스페이스 리스트 상태 인디케이터 (대기/작업중/완료/에러)
- macOS 시스템 알림 (pyobjc 또는 osascript)
- 설정 UI (폰트 선택, 테마 선택, 알림 설정)
- 설정 저장/로드 (JSON)

**핵심 파일:**
```
src/status/status_bar.py         # 하단 상태바 위젯
src/status/usage_monitor.py      # CTX/5H/7D 사용량 추적
src/status/session_watcher.py    # Claude Code 세션 파일 모니터링
src/status/state_detector.py     # PTY 출력 기반 상태 감지
src/notifications/notifier.py    # macOS 알림 발송
src/settings/settings_dialog.py  # 설정 다이얼로그
src/settings/font_picker.py      # 폰트 선택 위젯
src/settings/theme_picker.py     # 테마 선택 위젯
src/settings/config.py           # 설정 저장/로드
```

---

## Inter-Team Interface Contracts

> 병렬 작업 시 각 팀이 독립적으로 개발하되, 통합 시 충돌 없도록 인터페이스를 사전 합의한다.
> 모든 시그널/슬롯은 `src/models/` 또는 각 모듈의 public API로 정의한다.

### Signal/Slot Signatures

```python
# === Team A → Team B/D: 터미널 이벤트 ===
class PtyManager(QObject):
    pty_spawned = pyqtSignal(str)           # (pane_id) — PTY 프로세스 생성됨
    pty_exited = pyqtSignal(str, int)       # (pane_id, exit_code) — PTY 종료됨
    pty_output = pyqtSignal(str, bytes)     # (pane_id, data) — PTY 출력 데이터
    pty_cwd_changed = pyqtSignal(str, str)  # (pane_id, new_cwd) — 작업 디렉토리 변경

    def spawn(self, pane_id: str, cwd: str, shell: str = "") -> bool: ...
    def write(self, pane_id: str, data: bytes) -> None: ...
    def resize(self, pane_id: str, cols: int, rows: int) -> None: ...
    def kill(self, pane_id: str) -> None: ...
    def kill_all(self) -> None: ...

# === Team B → Team A: 레이아웃 이벤트 ===
class MainWindow(QMainWindow):
    pane_created = pyqtSignal(str, str)     # (pane_id, cwd) — 새 페인 생성 요청
    pane_closed = pyqtSignal(str)           # (pane_id) — 페인 닫기 요청
    pane_focused = pyqtSignal(str)          # (pane_id) — 페인 포커스 변경
    workspace_selected = pyqtSignal(str)    # (workspace_path) — 워크스페이스 선택

# === Team B → Team C: 위젯 이름 규약 ===
# QSS 셀렉터를 위한 objectName 컨벤션 (아래 별도 섹션 참조)

# === Team D → Team B/C: 상태 이벤트 ===
class UsageMonitor(QObject):
    usage_updated = pyqtSignal(dict)        # {"ctx": float, "5h": float, "7d": float} — 0.0~1.0

class StateDetector(QObject):
    # 페인별 Claude Code 상태
    state_changed = pyqtSignal(str, str)    # (pane_id, state) — "idle"|"thinking"|"tool_use"|"done"|"error"

# === Team C → 전체: 테마 이벤트 ===
class ThemeManager(QObject):
    theme_changed = pyqtSignal(dict)        # 전체 토큰 dict — 테마 전환 시 발행
    def get_color(self, key: str) -> str: ...
    def get_qss(self) -> str: ...
```

### objectName Convention (Team B ↔ Team C)

Team B가 위젯 생성 시 아래 objectName을 부여하고, Team C가 QSS에서 참조한다:

| Widget | objectName | QSS Selector |
|--------|-----------|--------------|
| 메인 윈도우 | `main_window` | `QMainWindow#main_window` |
| 사이드바 | `sidebar` | `QWidget#sidebar` |
| 사이드바 항목 | `sidebar_item` | `QWidget#sidebar_item` |
| 사이드바 활성 항목 | `sidebar_item_active` | `QWidget#sidebar_item_active` |
| 탭 바 | `tab_bar` | `QTabBar#tab_bar` |
| 스플릿 페인 | `pane_view` | `QWidget#pane_view` |
| 페인 헤더 | `pane_header` | `QWidget#pane_header` |
| 페인 디바이더 | `pane_divider` | `QWidget#pane_divider` |
| 터미널 위젯 | `terminal` | `QWidget#terminal` |
| 상태바 | `status_bar` | `QWidget#status_bar` |
| 설정 다이얼로그 | `settings_dialog` | `QDialog#settings_dialog` |

### Widget State Enums

```python
# src/models/enums.py

from enum import Enum

class PaneState(str, Enum):
    """워크스페이스/페인 상태 (사이드바 인디케이터용)"""
    IDLE = "idle"              # 대기 — 회색
    THINKING = "thinking"      # AI 사고 중 — 네온 시안 펄스
    TOOL_USE = "tool_use"      # 도구 실행 중 — 네온 마젠타 펄스
    DONE = "done"              # 완료 — 네온 그린
    ERROR = "error"            # 에러 — 빨간색
    WAITING = "waiting"        # 사용자 입력 대기 — 노란색

class SplitDirection(str, Enum):
    HORIZONTAL = "horizontal"  # 좌우 분할
    VERTICAL = "vertical"      # 상하 분할
```

---

## Keyboard Shortcuts

| Action | macOS | 비고 |
|--------|-------|------|
| 새 탭 | `Cmd+T` | 현재 워크스페이스 디렉토리에서 |
| 탭 닫기 | `Cmd+W` | PTY 프로세스도 종료 |
| 다음 탭 | `Cmd+Shift+]` | |
| 이전 탭 | `Cmd+Shift+[` | |
| n번째 탭 | `Cmd+1~9` | |
| 세로 분할 | `Cmd+D` | |
| 가로 분할 | `Cmd+Shift+D` | |
| 분할 닫기 | `Cmd+Shift+W` | |
| 다음 페인 포커스 | `Cmd+]` | |
| 이전 페인 포커스 | `Cmd+[` | |
| 사이드바 토글 | `Cmd+B` | |
| 설정 | `Cmd+,` | |
| 터미널 검색 | `Cmd+F` | |
| 폰트 크기 증가 | `Cmd+=` | |
| 폰트 크기 감소 | `Cmd+-` | |
| 폰트 크기 리셋 | `Cmd+0` | |

---

## Threading Strategy

```
┌─────────────────────────────────────────────┐
│  Main Thread (Qt Event Loop)                │
│  ├── UI 렌더링, 이벤트 처리                    │
│  ├── QSS 적용, 위젯 업데이트                   │
│  └── Signal/Slot 연결                        │
├─────────────────────────────────────────────┤
│  PtyReaderThread (per pane) — QThread       │
│  └── PTY stdout 읽기 → pty_output signal    │
│      (signal은 자동으로 메인 스레드에서 실행)     │
├─────────────────────────────────────────────┤
│  SessionWatcherThread — QThread             │
│  └── ~/.claude/ JSONL 파일 폴링 (500ms)      │
│      → usage_updated signal                 │
├─────────────────────────────────────────────┤
│  FileWatcherThread — QThread (optional)     │
│  └── 워크스페이스 파일 변경 감지               │
└─────────────────────────────────────────────┘

규칙:
- UI 업데이트는 반드시 메인 스레드에서 (signal/slot auto-connection)
- PTY I/O는 QThread에서 — QThread.run() 오버라이드
- 스레드 간 통신은 pyqtSignal만 사용 (직접 호출 금지)
- PTY 종료 시 QThread.quit() + wait(3000) + terminate()
```

---

## macOS Native Integration

```python
# 타이틀 바 — 네이티브 트래픽 라이트 + 커스텀 드래그 영역
# Qt.WindowType.FramelessWindowHint 사용하지 않음 (트래픽 라이트 유지)
# 대신 Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint

# 타이틀 바 영역:
# [🔴🟡🟢] ←72px→ [탭 바 ...] [+ 버튼]
# 트래픽 라이트 좌측 여백: 72px (macOS 기본)

MACOS = {
    "traffic_light_offset": 72,   # px — 탭 바 시작 위치
    "titlebar_height": 40,        # px
    "unified_titlebar": True,     # NSWindow.titlebarAppearsTransparent
}

# pyobjc를 통한 네이티브 설정:
# - NSWindow.titlebarAppearsTransparent = True
# - NSWindow.titleVisibility = .hidden
# - 배경색을 앱 bg_primary와 맞춤
```

---

## Design Specification — Neon Glow

> clabs-tauri의 네온 디자인을 PyQt6로 재해석. QSS는 CSS2 기반으로 box-shadow, transition, animation 미지원.
> QPainter + QGraphicsDropShadowEffect로 보완한다.

### Color Tokens

```python
# src/theme/tokens.py

COLORS = {
    # === Backgrounds (어두운 계층 구조) ===
    "bg_primary":    "#0a0a1a",   # 메인 앱 배경
    "bg_secondary":  "#12122a",   # 패널, 사이드바
    "bg_tertiary":   "#1a1a3e",   # 카드, 중첩 컨테이너
    "bg_hover":      "#242450",   # 호버 상태
    "bg_terminal":   "#08081a",   # 터미널 배경 (가장 어둡게)

    # === Text ===
    "text_primary":  "#ffffff",
    "text_secondary":"#e0e0e0",
    "text_muted":    "#8888aa",
    "text_disabled": "#555577",

    # === Accent (Neon Cyan — 주 강조색) ===
    "accent":        "#00FFCC",   # 메인 네온 (시안/민트)
    "accent_hover":  "#00DDaa",
    "accent_light":  "rgba(0, 255, 204, 0.10)",  # 10% — 배경 틴트
    "accent_medium": "rgba(0, 255, 204, 0.25)",  # 25% — 보더 호버
    "accent_strong": "rgba(0, 255, 204, 0.40)",  # 40% — 보더 포커스

    # === Secondary Accent (Neon Magenta) ===
    "accent2":       "#FF66FF",   # 보조 네온 (마젠타)
    "accent2_light": "rgba(255, 102, 255, 0.10)",

    # === Status ===
    "status_success":"#00FF88",   # 녹색
    "status_warning":"#FFCC00",   # 노란색
    "status_error":  "#FF4466",   # 빨간색
    "status_info":   "#00AAFF",   # 파란색

    # === Usage Spectrum (상태바 그라데이션) ===
    "usage_low":     "#00FFCC",   # 0-50% — 민트
    "usage_mid":     "#FFCC00",   # 50-80% — 노란색
    "usage_high":    "#FF8800",   # 80-95% — 주황색
    "usage_critical":"#FF4466",   # 95-100% — 빨간색

    # === Borders ===
    "border_default":"#333366",
    "border_hover":  "rgba(0, 255, 204, 0.30)",
    "border_focus":  "rgba(0, 255, 204, 0.50)",

    # === Terminal ANSI Colors ===
    "ansi_black":    "#1a1a3e",
    "ansi_red":      "#FF4466",
    "ansi_green":    "#00FF88",
    "ansi_yellow":   "#FFCC00",
    "ansi_blue":     "#00AAFF",
    "ansi_magenta":  "#FF66FF",
    "ansi_cyan":     "#00FFCC",
    "ansi_white":    "#e0e0e0",
}
```

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `radius_sm` | 4px | 스크롤바 thumb, 뱃지 |
| `radius_md` | 8px | 버튼, 탭, 인풋 |
| `radius_lg` | 12px | 카드, 모달, 패널 |
| `radius_xl` | 16px | 큰 컨테이너 |
| `radius_full` | 9999px | 필 모양 뱃지, 프로그레스 바 |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| UI Text | SF Pro Display, Inter, system-ui | 13px | 400 |
| UI Label | 위와 동일 | 12px | 500 |
| UI Header | 위와 동일 | 16px | 600 |
| Terminal | JetBrains Mono, Fira Code, Menlo | 14px | 400 |
| Status Bar | 터미널 폰트와 동일 | 11px | 500 |

### Spacing Scale

| Token | Value |
|-------|-------|
| `xs` | 4px |
| `sm` | 8px |
| `md` | 16px |
| `lg` | 24px |
| `xl` | 32px |

### Layout Dimensions

| Component | Value |
|-----------|-------|
| Title Bar Height | 40px |
| Sidebar Width (default) | 240px |
| Sidebar Width (min/max) | 180px / 400px |
| Tab Bar Height | 36px |
| Status Bar Height | 28px |
| Scrollbar Width | 8px |
| Pane Divider Width | 4px |

### Glow Effects — PyQt6 구현 전략

QSS는 `box-shadow`를 지원하지 않으므로 세 가지 기법을 조합한다:

#### 1. QGraphicsDropShadowEffect (간단한 글로우)
```python
# 위젯에 네온 글로우 적용
def apply_glow(widget, color="#00FFCC", radius=25, offset=(0, 0)):
    effect = QGraphicsDropShadowEffect()
    effect.setOffset(*offset)
    effect.setBlurRadius(radius)
    effect.setColor(QColor(color))
    widget.setGraphicsEffect(effect)
```
- 용도: 사이드바 활성 항목, 포커스된 인풋, 활성 탭
- 제한: 위젯당 1개만 가능

#### 2. QPainter 멀티레이어 글로우 (커스텀 위젯)
```python
# paintEvent에서 여러 겹의 반투명 라운드 렉트를 그려 글로우 효과
for i in range(layers, 0, -1):
    expand = i * 3.0
    alpha = int(40 * (1 - i / layers))
    color.setAlpha(alpha)
    painter.drawRoundedRect(rect.adjusted(-expand, ...), radius + i, radius + i)
```
- 용도: 네온 버튼, 네온 프레임, 프로그레스 바
- 장점: 완전한 커스터마이징 가능

#### 3. QSS 그라데이션 보더 (순수 스타일시트)
```css
/* 호버 시 보더 색상을 반투명 네온으로 */
QWidget:hover {
    border: 2px solid rgba(0, 255, 204, 0.3);
}
QWidget:focus {
    border: 2px solid rgba(0, 255, 204, 0.5);
}
```
- 용도: 일반 위젯 호버/포커스 상태
- 가장 가볍고 성능 좋음

### Animation — QPropertyAnimation

```python
# 펄스 글로우 애니메이션
anim = QPropertyAnimation(effect, b"blurRadius")
anim.setDuration(1500)
anim.setStartValue(15)
anim.setEndValue(35)
anim.setEasingCurve(QEasingCurve.Type.InOutSine)
anim.setLoopCount(-1)
```
- 용도: 작업 중 상태 인디케이터, 활성 프로세스 표시
- `prefers-reduced-motion` 감지 시 비활성화

### Glassmorphism (모달/오버레이)
```python
# 반투명 배경 + 블러
GLASS = {
    "bg": "rgba(18, 18, 42, 0.85)",
    "border": "rgba(255, 255, 255, 0.08)",
}
# QGraphicsBlurEffect 또는 플랫폼 네이티브 블러 사용
```

---

## Development Phases

### Phase 0 — Project Skeleton
> 모든 팀이 시작하기 전 기반 세팅

**작업:**
- [ ] Python 프로젝트 구조 생성 (src/, resources/, tests/)
- [ ] `requirements.txt` 작성 — 버전 고정:
  ```
  PyQt6>=6.7,<7.0
  pyte>=0.8.2
  pyobjc-core>=10.0      # macOS native integration
  pyobjc-framework-Cocoa>=10.0
  ```
- [ ] `src/main.py` — 앱 진입점, QApplication 생성
- [ ] `src/app.py` — QApplication 설정, 테마 로드 초기 구조
- [ ] `src/models/enums.py` — PaneState, SplitDirection 등 공유 Enum
- [ ] 전체 패키지 `__init__.py` 생성 (terminal/, ui/, models/, theme/, widgets/, status/, notifications/, settings/)
- [ ] 빈 모듈 스켈레톤 생성 (각 팀 핵심 파일의 빈 클래스/함수 + docstring)
- [ ] `models/pane_tree.py`, `models/workspace.py` 데이터 모델 스켈레톤
- [ ] `resources/` 디렉토리 구조 (fonts/, themes/, icons/)
- [ ] `.claude/settings.json` 팀 구조 설정

**산출물:** `python src/main.py`로 빈 윈도우가 뜨는 상태, 모든 패키지 import 가능
**검증:** `python -c "from src.terminal import pty_manager; from src.ui import main_window; from src.theme import tokens"` 성공
**담당:** 전체 (순차)

---

### Phase 1 — Foundation (병렬 작업 시작)
> 각 팀이 독립적으로 핵심 모듈을 구현

#### Team A: 터미널 PoC
- [ ] PTY 매니저: subprocess + pty 모듈로 셸 스폰
- [ ] 터미널 위젯 PoC: pyte 기반 VT100 에뮬레이터 + QWidget 렌더링
  - (QTermWidget 빌드 성공 시 교체, 실패 시 pyte fallback 유지)
- [ ] 키 입력 → PTY 쓰기 파이프라인
- [ ] PTY 출력 → 화면 렌더링 파이프라인
- [ ] 터미널 리사이즈 처리
- [ ] 한글 IME 조합 입력 PoC 검증 (inputMethodEvent 처리, pyte fallback 시 조합 중 상태 렌더링)
- [ ] 단위 테스트: PTY 스폰/종료, 입출력 파이프라인 (`tests/test_pty_manager.py`)

#### Team B: 레이아웃 뼈대
- [ ] QMainWindow + QSplitter 기본 레이아웃 (사이드바 | 작업 영역)
- [ ] 사이드바: QListWidget 기반 워크스페이스 리스트
- [ ] 탭 바: QTabWidget 기반 멀티 터미널 탭
- [ ] PaneNode 바이너리 트리 자료구조 구현 (`models/pane_tree.py`)
- [ ] 기본 스플릿 뷰 (QSplitter 중첩)
- [ ] `pane_divider.py` — 스플릿 리사이즈 핸들 기본 구현
- [ ] `models/workspace.py` — 워크스페이스/탭 상태 모델 기본 구현
- [ ] 위젯 objectName/클래스명 확정 (Team C QSS 연동 기준)
- [ ] 단위 테스트: PaneNode 트리 조작 (`tests/test_pane_tree.py`), 워크스페이스 모델 (`tests/test_workspace.py`)

#### Team C: 디자인 토큰 + 기본 테마
- [ ] `tokens.py` — 전체 디자인 토큰 정의
- [ ] `neon_theme.qss` — 글로벌 QSS 작성 (Team B와 objectName/클래스명 합의 후 전체 위젯 커버)
- [ ] `effects.py` — QGraphicsDropShadowEffect 유틸리티
- [ ] `theme_manager.py` — 테마 로드/전환 기본 구조
- [ ] 기본 네온 다크 테마 적용

#### Team D: 상태바 + 설정 기반
- [ ] 상태바 위젯 (CTX / 5H / 7D 플레이스홀더)
- [ ] `config.py` — JSON 기반 설정 저장/로드
- [ ] 기본 설정 다이얼로그 껍데기
- [ ] `session_watcher.py` — Claude Code 세션 파일 탐색/모니터링 기초 구현 (파일 경로 탐색, 변경 감지)
- [ ] `state_detector.py` — PTY 출력 기반 상태 감지 기초 구현 (정규식 패턴 정의, 상태 enum)
- [ ] `usage_monitor.py` — 사용량 데이터 파싱 기초 구현 (Statusline JSON 스키마 정의)

**산출물:** 사이드바 + 탭 + 스플릿 뷰에 터미널이 렌더링되고, 네온 테마가 적용된 상태

---

### Phase 2 — Integration
> Phase 1 결과물을 통합하고 인터랙션 연결

#### Team A + B: 터미널 ↔ 레이아웃 연결
- [ ] 사이드바 워크스페이스 클릭 → 해당 디렉토리에서 PTY 스폰
- [ ] 탭 추가 → 새 PTY 생성, 탭 닫기 → PTY 종료
- [ ] 스플릿 → 새 PTY 생성, 스플릿 해제 → PTY 종료
- [ ] 탭/스플릿 전환 시 PTY 세션 유지 (destroy 하지 않음)

#### Team A + C: 터미널 ↔ 테마 연결
- [ ] 터미널 위젯에 ANSI 컬러 토큰 적용 (`tokens.py` → 터미널 색상 매핑)
- [ ] 터미널 폰트/배경색 테마 연동 (`terminal_config.py` ↔ `theme_manager.py`)
- [ ] 테마 변경 시 터미널 위젯 실시간 반영

#### Team C: 커스텀 위젯 적용
- [ ] NeonButton — QPainter 멀티레이어 글로우
- [ ] NeonFrame — 패널 컨테이너 글로우
- [ ] NeonProgressBar — 상태바 사용량 프로그레스
- [ ] NeonTabBar — 활성 탭 글로우 인디케이터
- [ ] 사이드바/탭바/상태바에 커스텀 위젯 교체 적용

#### Team C + D: 상태바 ↔ 커스텀 위젯 연결
- [ ] NeonProgressBar ↔ usage_monitor 데이터 바인딩 (시그널/슬롯 인터페이스 합의)
- [ ] 상태 인디케이터에 글로우 이펙트 적용 (펄스 애니메이션 — 작업 중 상태)
- [ ] 사용량 구간별 색상 변경 (usage_low → usage_critical 스펙트럼)

#### Team D: 상태 감지 연결
- [ ] PTY 출력 파싱으로 Claude Code 상태 감지 (Phase 1 기초 위에 실 연동)
- [ ] 상태바에 실제 CTX 값 표시 (Statusline JSON 연동)
- [ ] 워크스페이스 리스트에 상태 인디케이터 표시

**산출물:** 완전히 동작하는 멀티 터미널 + 네온 UI

---

### Phase 3 — Features
> 고급 기능 추가

#### Team A: 터미널 고급 기능
- [ ] 줄간격 설정 적용
- [ ] 터미널 검색 (Ctrl+F)
- [ ] 터미널 텍스트 선택/복사 개선
- [ ] 스크롤백 버퍼 크기 설정

#### Team B: 고급 UX
- [ ] 워크스페이스 rename (더블클릭 인라인 편집)
- [ ] 탭 rename
- [ ] 탭 드래그 앤 드롭 재배치
- [ ] 탭 → 스플릿 영역 간 드래그 앤 드롭
- [ ] 사이드바 리사이즈 (드래그)
- [ ] 레이아웃 상태 저장/복원

#### Team C: 테마 시스템
- [ ] 테마 프리셋 추가 (Dracula, Nord, Tokyo Night 등)
- [ ] JetBrains IDE 테마 임포트 (.icls 파싱)
- [ ] Terminal.app 테마 임포트 (.terminal 파싱)
- [ ] 커스텀 컬러 스킴 에디터
- [ ] 테마 전환 시 실시간 미리보기

#### Team D: 알림 + 설정
- [ ] macOS 시스템 알림 구현
- [ ] Claude Code Hooks 연동 (Stop/StopFailure/Notification)
- [ ] 프로젝트별 알림 on/off
- [ ] 폰트 선택 UI (시스템 폰트 목록 + 미리보기)
- [ ] 설정 다이얼로그 완성

**산출물:** 풀 기능 앱

---

### Phase 4 — Polish & Ship
> 안정화, 최적화, 배포 준비

- [ ] 통합 테스트 작성 (터미널 ↔ 레이아웃 ↔ 테마 E2E 시나리오)
- [ ] 메모리 누수 점검 (PTY 프로세스 정리)
- [ ] 성능 최적화 (터미널 렌더링 프레임 드롭)
- [ ] 에러 핸들링 강화
- [ ] PyInstaller 또는 cx_Freeze로 .app 번들 생성
- [ ] DMG 패키징
- [ ] README.md 작성
- [ ] 스크린샷/데모 GIF 제작

---

## Key Technical Decisions

### 터미널 위젯 전략
1. **1순위:** QTermWidget (Qt6 빌드) — 네이티브 VTE, 완벽한 터미널 호환
2. **2순위 (fallback):** pyte + 커스텀 QWidget — 순수 Python, pip 설치 가능
   - pyte: VT100 에뮬레이터 (화면 버퍼 관리)
   - QWidget: 화면 버퍼를 QPainter로 렌더링
   - 한계: 256색/트루컬러, 마우스 이벤트, 일부 이스케이프 시퀀스 제한

### 스플릿 뷰 구조
clabs-tauri와 동일한 바이너리 트리 구조 채택:
```python
@dataclass
class PaneLeaf:
    id: str
    name: str

@dataclass
class PaneSplit:
    id: str
    direction: Literal["horizontal", "vertical"]
    ratio: float  # 0.0 ~ 1.0
    first: PaneNode
    second: PaneNode

PaneNode = PaneLeaf | PaneSplit
```

### PTY 관리
- 각 터미널 탭/스플릿 페인마다 독립 PTY 프로세스
- 탭 전환 시 PTY 유지 (QWidget hide/show, destroy 하지 않음)
- 앱 종료 시 모든 PTY 프로세스 정리

### 사용량 모니터링
- **1순위:** Claude Code Statusline JSON (공식 API)
- **2순위:** 세션 JSONL 파일 폴링 (500ms)
- **3순위:** OAuth API 직접 호출 (비공식)

---

## File Structure

```
JBTerminal/
├── CLAUDE.md                    # 이 문서
├── PROJECT.md                   # 프로젝트 기획서
├── requirements.txt
├── .gitignore
├── src/
│   ├── main.py                  # 앱 진입점
│   ├── app.py                   # QApplication 설정, 테마 로드
│   │
│   ├── terminal/                # [Team A] 터미널 코어
│   │   ├── __init__.py
│   │   ├── pty_manager.py       # PTY 프로세스 풀
│   │   ├── terminal_widget.py   # 터미널 에뮬레이터 위젯
│   │   └── terminal_config.py   # 터미널 설정
│   │
│   ├── ui/                      # [Team B] UI 레이아웃
│   │   ├── __init__.py
│   │   ├── main_window.py       # QMainWindow
│   │   ├── sidebar.py           # 워크스페이스 리스트
│   │   ├── tab_bar.py           # 멀티 터미널 탭 바
│   │   ├── split_pane.py        # 스플릿 뷰 컨테이너
│   │   ├── pane_view.py         # 개별 페인
│   │   └── pane_divider.py      # 스플릿 리사이즈 핸들
│   │
│   ├── models/                  # 데이터 모델
│   │   ├── __init__.py
│   │   ├── enums.py             # PaneState, SplitDirection 등
│   │   ├── pane_tree.py         # PaneNode 바이너리 트리
│   │   └── workspace.py         # 워크스페이스/탭 상태
│   │
│   ├── theme/                   # [Team C] 디자인 시스템
│   │   ├── __init__.py
│   │   ├── tokens.py            # 디자인 토큰
│   │   ├── neon_theme.qss       # 글로벌 스타일시트
│   │   ├── theme_manager.py     # 테마 관리
│   │   ├── effects.py           # 글로우 이펙트 유틸
│   │   └── presets/             # 테마 프리셋
│   │       ├── __init__.py
│   │       ├── default_dark.py
│   │       └── default_light.py
│   │
│   ├── widgets/                 # [Team C] 커스텀 위젯
│   │   ├── __init__.py
│   │   ├── neon_button.py
│   │   ├── neon_frame.py
│   │   ├── neon_progress.py
│   │   └── neon_tab_bar.py
│   │
│   ├── status/                  # [Team D] 상태 모니터링
│   │   ├── __init__.py
│   │   ├── status_bar.py        # 하단 상태바
│   │   ├── usage_monitor.py     # 사용량 추적
│   │   ├── session_watcher.py   # 세션 파일 모니터링
│   │   └── state_detector.py    # 상태 감지
│   │
│   ├── notifications/           # [Team D] 알림
│   │   ├── __init__.py
│   │   └── notifier.py
│   │
│   └── settings/                # [Team D] 설정
│       ├── __init__.py
│       ├── settings_dialog.py
│       ├── font_picker.py
│       ├── theme_picker.py
│       └── config.py
│
├── resources/
│   ├── fonts/
│   ├── themes/
│   └── icons/
│
└── tests/
    ├── conftest.py              # QApplication fixture
    ├── test_pty_manager.py
    ├── test_pane_tree.py
    └── test_workspace.py
```

---

## Conventions

### Code Style
- Python 3.11+, type hints 사용 (return type 포함)
- 클래스명: PascalCase, 함수/변수: snake_case
- 상수: UPPER_SNAKE_CASE
- private 메서드/속성: `_prefix`
- 파일당 1개 주요 클래스 원칙

### PyQt6 Patterns
- 시그널 네이밍: `<noun>_<verb_past>` (e.g. `workspace_selected`, `pane_created`)
- 슬롯 네이밍: `_on_<signal_name>` (e.g. `_on_workspace_selected`)
- objectName: snake_case (e.g. `sidebar_item`) — QSS 셀렉터 기준
- 위젯 생성 시 반드시 `self.setObjectName("...")` 호출
- UI 업데이트는 메인 스레드에서만 (QThread → signal → slot)

### QSS / Theme
- 색상 하드코딩 금지 — 반드시 `tokens.py` 참조
- QSS에서 동적 색상 필요 시 `ThemeManager.get_qss()`로 토큰 치환
- 커스텀 위젯은 QSS 대신 QPainter 사용 (글로우 등)

### Git
- 커밋 메시지: 영문, conventional commits (feat/fix/refactor/docs/test)
- 브랜치: `phase-N/team-X/feature-name` (e.g. `phase-1/team-a/pty-manager`)
- PR 단위: 팀별 Phase 완료 시 1개 PR

### Testing
- 테스트 파일: `tests/test_<module_name>.py`
- 테스트 실행: `python -m pytest tests/`
- UI 위젯 테스트 시 `QApplication` 인스턴스 필요 — conftest.py에서 fixture 제공
