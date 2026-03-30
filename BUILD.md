# JBTerminal 빌드 가이드

## 개발 환경 실행

```bash
cd /Users/workspace/JBTerminal
python -m src.main
```

> Anaconda 환경에서는 `QT_PLUGIN_PATH` 설정이 필요할 수 있음:
> ```bash
> QT_PLUGIN_PATH=$(python -c "import PyQt6,os;print(os.path.join(os.path.dirname(PyQt6.__file__),'Qt6','plugins'))") python -m src.main
> ```

---

## .app 번들 빌드

### 왜 별도 venv가 필요한가

Anaconda에는 시스템 Qt5(`libQt5*.dylib`)가 포함되어 있고, `pip install PyQt6`는 Qt6를 설치한다.
PyInstaller가 빌드할 때 두 Qt 버전이 섞여 들어가면서 `cocoa` 플러그인 로드에 실패한다.

**깨끗한 venv에서 빌드해야 Qt6만 번들에 포함됨.**

### 빌드 순서

```bash
# 1. 빌드 전용 venv 생성
python -m venv /tmp/jbt_venv
source /tmp/jbt_venv/bin/activate

# 2. 의존성 설치
pip install PyQt6 pyte pyobjc-core pyobjc-framework-Cocoa pyinstaller

# 3. 빌드
cd /Users/workspace/JBTerminal
rm -rf dist build
pyinstaller JBTerminal.spec --noconfirm

# 4. 결과 확인
open dist/JBTerminal.app
```

### 빌드 결과물

```
dist/JBTerminal.app
├── Contents/
│   ├── Info.plist          # 한국어 로컬라이제이션, 다크 모드 선언
│   ├── MacOS/
│   │   └── JBTerminal      # 실행 바이너리
│   └── Frameworks/
│       └── PyQt6/Qt6/
│           ├── lib/         # Qt6 프레임워크
│           └── plugins/
│               └── platforms/
│                   └── libqcocoa.dylib  # macOS 네이티브 렌더링
```

### Info.plist 핵심 설정

| 키 | 값 | 역할 |
|----|-----|------|
| `CFBundleLocalizations` | `[ko, en, ja, zh_CN]` | 시스템 다이얼로그 한국어 표시 |
| `CFBundleDevelopmentRegion` | `ko` | 기본 언어 |
| `NSRequiresAquaSystemAppearance` | `false` | 다크 모드 지원 |
| `NSHighResolutionCapable` | `true` | Retina 디스플레이 지원 |

### 트러블슈팅

**Q: `Could not find the Qt platform plugin "cocoa"`**
- Anaconda 환경에서 빌드하면 Qt5/Qt6 충돌 발생
- 반드시 깨끗한 venv에서 빌드할 것

**Q: 파일 다이얼로그가 영어로 나옴**
- `python -m src.main`(비번들)에서는 `.app` 번들이 아니라 macOS가 로컬라이제이션 정보를 못 읽음
- `.app` 번들로 빌드하면 `CFBundleLocalizations` 설정에 의해 한국어로 표시됨

**Q: 타이틀 바가 회색으로 깜빡임**
- `NSApp.setAppearance_(DarkAqua)`가 윈도우 생성 전에 호출되어야 함
- `app.py`의 `_setup_macos_post_app()`에서 처리

---

## DMG 패키징 (배포용)

```bash
# create-dmg 설치 (homebrew)
brew install create-dmg

# DMG 생성
create-dmg \
  --volname "JBTerminal" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "JBTerminal.app" 175 120 \
  --app-drop-link 425 120 \
  "JBTerminal.dmg" \
  "dist/JBTerminal.app"
```
