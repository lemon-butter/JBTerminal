# JBTerminal

AI CLI 도구(Claude Code 등)를 위한 데스크톱 터미널 애플리케이션.

## 목표

네이티브 터미널 에뮬레이터를 내장하여 한글 IME 조합 입력이 완벽하게 동작하고, AI 작업 상태를 실시간으로 추적/관리할 수 있는 GUI 앱.

## 기술 스택

- **언어:** Python
- **GUI 프레임워크:** PyQt6
- **터미널 위젯:** QTermWidget (네이티브 터미널 에뮬레이터)
- **빌드/배포:** PyInstaller 또는 cx_Freeze

## 핵심 기능

### 1. 네이티브 터미널
- QTermWidget 기반 터미널 에뮬레이터
- 한글 IME 조합 입력 완벽 지원 (xterm.js의 한계 해결)
- 줄간격 설정 (특수문자 아스키아트가 깨지지 않도록)

### 2. 사이드바 (SNB) - 워크스페이스 리스트
- 왼쪽 사이드바에 프로젝트/워크스페이스 목록 표시
- 클릭하면 해당 프로젝트 디렉토리에서 우측 작업 영역에 터미널 세션 열기
- 프로젝트 추가/삭제/정렬
- **워크스페이스 이름 변경 (rename)** 지원 (더블클릭 또는 우클릭 메뉴)

### 3. 멀티 터미널 작업 영역 (JetBrains 스타일)
- 워크스페이스 선택 시 우측 작업 영역에 터미널 표시
- **탭 기반 멀티 터미널:** 하나의 워크스페이스에서 여러 터미널을 탭으로 열기 (2개, 3개 이상 가능)
- **터미널 탭 이름 변경 (rename):** 각 탭에 커스텀 이름 부여 가능
- **Split 뷰:**
  - 좌/우 분할 (horizontal split)
  - 상/하 분할 (vertical split)
  - 다중 분할 조합 가능
- **드래그 앤 드롭:** 탭을 드래그하여 split 영역 간 이동/재배치
- JetBrains IDE의 터미널 작업 영역 UX를 참고

### 4. 설정
- **폰트 설정:**
  - 시스템에 설치된 폰트 목록에서 선택
  - 폰트 크기 조절
  - 미리보기 지원
- **테마 설정:**
  - JetBrains IDE 터미널 테마 가져오기 지원
  - macOS 기본 터미널(Terminal.app) 테마 가져오기 지원
  - 빌트인 테마 제공 (Dark, Light 등)
  - 커스텀 컬러 스킴 편집

### 5. 실시간 상태 표시 & 사용량 모니터링
- 각 프로젝트(터미널 세션)의 현재 진행 상태를 워크스페이스 리스트에 실시간 표시
- AI CLI 도구의 출력을 파싱하여 상태 감지 (대기중, 작업중, 완료, 에러 등)
- cmux 스타일의 상태 인디케이터
- **하단 상태바에 사용량 표시** (clabs-tauri 참고):
  - **CTX** — 컨텍스트 윈도우 사용량 (%, 토큰 수)
  - **5H** — 5시간 레이트 리밋 사용량 (%, 리셋 시간)
  - **7D** — 7일 레이트 리밋 사용량 (%, 리셋 시간)
  - **Task** — 현재 작업 경과 시간

### 6. 알림 시스템
- 작업 완료/에러 발생 시 시스템 알림(macOS Notification Center)
- 프로젝트별 알림 설정 on/off

## 참고 프로젝트

### cmux
- **GitHub:** https://github.com/manaflow-ai/cmux
- **구조:** Swift + AppKit 네이티브 macOS 앱
- **터미널:** libghostty (Ghostty 터미널 라이브러리) + Metal GPU 렌더링
- **참고할 점:** 워크스페이스 리스트 UI, 실시간 상태 표시, 알림 시스템
- **한계:** macOS 전용, 빌드가 매우 복잡 (Zig 툴체인 + Metal 셰이더 + Xcode 필요)

### clabs-tauri
- **GitHub (원본):** https://github.com/vibelabs-web/clabs-tauri
- **GitHub (fork):** https://github.com/lemon-butter/clabs-tauri
- **구조:** Tauri + React + TypeScript
- **터미널:** xterm.js (웹 기반 터미널 에뮬레이터)
- **참고할 점:** 전체 UI 구성, 테마 시스템, PTY 연동 방식, 붙여넣기 안전 검사, **하단 상태바 (CTX/5H/7D 사용량 표시)**
- **한계:** xterm.js의 한글 IME 조합 입력 문제 (compositionstart/end로 우회해도 완벽하지 않음), 줄간격 기본값(1.4)이 높아 아스키아트 깨짐

## 기술 검증 결과

### 알림 시스템 — 가능
- **Plan A (공식):** Claude Code Hooks 활용
  - `~/.claude/settings.json`에 훅 설정 → `Stop`, `StopFailure`, `Notification` 등 이벤트마다 구조화된 JSON 수신
  - HTTP 훅: 앱 내 localhost 서버로 POST 수신
  - Command 훅: 셸 스크립트가 JSON을 stdin으로 받아 앱에 전달 (Unix 소켓 등)
- **Plan A-2:** PTY 바이트 스트림에서 OSC 9 시퀀스 (`\033]9;...\007`) 직접 파싱 (Claude Code가 턴 종료 시 자동 emit)
- **Plan B (clabs 방식):** JSONL 세션 파일 폴링으로 상태 변화 감지
- macOS 알림: `pyobjc` (UNUserNotificationCenter) 또는 `osascript` 호출

### 사용량 모니터링 (CTX / 5H / 7D) — 가능
- **Plan A (공식):** Claude Code Statusline JSON
  - `~/.claude/settings.json`에 statusline 스크립트 설정
  - 매 응답마다 `context_window` (used_percentage, 토큰 수, context_window_size) + `rate_limits` (five_hour/seven_day 사용량, resets_at) JSON을 stdin으로 수신
  - 앱에서 파일로 저장 후 `QFileSystemWatcher`로 감지
- **Plan B (clabs 방식):**
  - CTX: `~/.claude/projects/{프로젝트}/*.jsonl` 세션 파일 직접 파싱 (500ms 폴링)
  - 5H/7D: Anthropic OAuth API (`GET https://api.anthropic.com/api/oauth/usage`) 직접 호출
  - OAuth 토큰: macOS Keychain에서 `security find-generic-password -s "Claude Code-credentials"` 로 읽기
  - 비공식 API이므로 변경 가능성 있음

### Split 뷰 + 드래그 앤 드롭 — 가능
- **QSplitter** 중첩으로 상하/좌우 분할 (Qt 내장, 난이도 낮음)
- **PyQt6Ads** (`pip install PyQt6Ads`) — Qt Advanced Docking System
  - JetBrains 스타일 탭 + split + 드래그 앤 드롭 도킹 인프라 제공
  - 레이아웃 저장/복원 (perspectives) 지원
- 터미널 위젯은 각 도크 위젯 안에 QTermWidget 인스턴스로 배치
- QTerminal이 이미 QTermWidget + QSplitter로 split 뷰 구현하여 검증됨

### QTermWidget 빌드 (가장 큰 리스크)
- lxqt/qtermwidget v2.3.0이 Qt6 지원 (qtbase >= 6.6.0 필요)
- Python 바인딩은 소스 빌드 필요 (`pip install` 불가) — CMake + SIP + Qt6 헤더 필요
- **대안:** termqt (순수 Python, `pip install termqt`) 또는 pyte + 커스텀 QWidget (VT100 호환성 제한)
- **권장:** 먼저 QTermWidget macOS 빌드를 PoC로 검증

## 아키텍처 메모

### 왜 xterm.js가 아닌 QTermWidget인가
- xterm.js는 웹 기반이라 브라우저의 textarea로 입력을 받음
- IME 조합 입력(한글, 일본어, 중국어)이 근본적으로 불완전
- compositionstart/compositionend 이벤트로 우회 시도해도 중복 입력 또는 누락 발생
- QTermWidget은 네이티브 터미널 에뮬레이터라 OS의 IME를 직접 사용하므로 문제 없음

### 왜 TUI(Textual, Bubbletea)가 아닌 GUI인가
- TUI는 터미널 안에서 실행되는 프로그램 (이미 터미널이 있어야 함)
- 독립 데스크톱 앱으로 터미널 자체를 제공하려면 GUI 프레임워크 필요
- TUI로 만들면 iTerm/Terminal.app 안에서 실행해야 하므로 별도 앱의 의미가 없음

## 개발 환경

- macOS (주 타겟)
- Python 3.11+
- PyQt6

## 디렉토리 구조 (예정)

```
JBTerminal/
  src/
    main.py              # 앱 진입점
    terminal/            # QTermWidget 래퍼
    sidebar/             # 워크스페이스 리스트 UI
    status/              # 상태 감지 및 표시
    notifications/       # 알림 시스템
    settings/            # 폰트, 테마 등 설정
  resources/
    fonts/
    themes/
  requirements.txt
  README.md
```
