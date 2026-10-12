# 업비트 포켓(Pocket) 관리 도구

업비트 공식 API를 이용해 **메인포켓 / 서브포켓**의 자산을 조회하고,
포켓 간 자산 이동을 수행하는 도구입니다.

브라우저에서 쓰는 **웹 UI**와 터미널에서 쓰는 **CLI** 두 가지 진입점을 제공합니다.
두 진입점이 같은 도메인 로직(`upbit_pocket/service.py`)을 공유합니다.

## 빠른 시작

Windows에서는 `.bat` 파일을 더블클릭만 하면 됩니다.
가상환경(`.venv`)이 없으면 자동으로 만들고, 필요한 패키지도 자동으로 설치합니다.

| 파일 | 용도 |
| --- | --- |
| **`setup.bat`** | 최초 1회 설정 — 가상환경 생성, 패키지 설치, `.env` 생성 |
| **`run_web.bat`** | 웹 UI 실행 → http://127.0.0.1:5000 |
| **`run_cli.bat`** | 터미널 실행 (`run_cli.bat check` 처럼 인자를 넘김) |

### 1. 최초 설정

```bat
setup.bat
```

가상환경을 만들고, `requirements.txt`를 설치하고, `.env.example`을 `.env`로 복사한 뒤
메모장으로 열어 API Key를 입력할 수 있게 안내합니다.

### 2. 웹 UI 실행

```bat
run_web.bat
```

브라우저가 자동으로 열립니다. 이미 실행 중이면 포트 충돌이 나므로 창을 먼저 닫아주세요.

### 3. 터미널 실행

```bat
run_cli.bat                 REM 자산 현황
run_cli.bat check           REM 연결/권한 점검
run_cli.bat pockets         REM 포켓 목록
run_cli.bat move            REM 특정 자산 이동 (드라이런)
run_cli.bat move-all --execute
run_cli.bat history --limit 50
```

수동으로 실행하려면 가상환경 파이썬을 직접 쓰면 됩니다.

```powershell
.\.venv\Scripts\python.exe web.py
.\.venv\Scripts\python.exe main.py status
```

가상환경 없이 시스템 파이썬으로 실행하려면 먼저 `pip install -r requirements.txt`를 하면 됩니다.

### 웹 화면

| 페이지 | 경로 | 설명 |
| --- | --- | --- |
| 대시보드 | `/` | 포켓별 자산 현황, 시세 평가, 자산 이동 |
| 이전 내역 | `/history` | 포켓 간 이전 기록 조회 (자산·상태 필터) |

#### 브랜드 로고 바꾸기

좌측 상단 로고 자리에 업비트 공식 로고를 쓰고 싶다면, 아래 이름 중 하나로
`upbit_pocket/web/static/` 에 파일을 넣고 서버를 다시 시작하세요.

```
upbit-logo.svg   (권장)   upbit-logo.png   upbit-logo.webp   logo.svg   logo.png
```

파일이 있으면 자동으로 로고를 쓰고, 없으면 기본 마크로 돌아갑니다.

```powershell
# 업비트 공식 이미지 다운로드 후 이름을 upbit-logo.png 으로 저장
curl.exe -o upbit_pocket\web\static\upbit-logo.png "다운로드한_로고_URL"
```

로고는 업비트 상표이므로 **저장소에는 포함하지 않습니다** (`.gitignore` 처리됨).
직접 받은 파일을 로컬에만 두고 쓰세요.

대시보드에서 하는 일:

1. **자산 이동** 폼에서 출발 포켓 → 도착 포켓 → 자산(또는 `전체 자산`) → 수량 선택
2. **이동 계획 보기** — API를 호출하지 않고 계획만 미리 계산 (잠긴 자산 자동 제외)
3. **위 계획대로 실행** — 브라우저 확인 창을 거쳐 실제 이전 요청 전송
4. 30초마다 자동 갱신 (끄고 켤 수 있음)

## 빠른 시작 (터미널)

| 명령 | 설명 |
| --- | --- |
| `python main.py` / `status` | 모든 포켓의 자산 현황 (시세 기반 원화 평가 포함) |
| `python main.py pockets` | 메인포켓·서브포켓 목록 (UUID 포함) |
| `python main.py check` | API 연결 및 권한 점검 |
| `python main.py move` | 특정 자산(개별 수량 또는 전량)을 다른 포켓으로 이동 |
| `python main.py move-all` | 출발 포켓의 자산 전체를 다른 포켓으로 이동 |
| `python main.py history` | 포켓 자산 이전 내역 조회 |

배치 파일로는 `run_cli.bat check`처럼 같은 인자를 그대로 넘기면 됩니다.

## 준비 사항

### 1. API Key 발급

[업비트 API Key 관리](https://upbit.com/mypage/open_api_management)에서 발급받습니다.

* **포켓 관리 권한이 반드시 필요합니다.** ([포켓 관리](https://docs.upbit.com/kr/reference/pocket-overview) 권한은 메인포켓에서만 발급 가능)
* 조회만 할 거라면 `[자산조회]` + `[포켓관리]`면 충분합니다.
* 발급한 Key의 **호출 IP 목록**에 현재 PC의 IP를 등록해야 합니다.

### 2. 서브포켓 생성

이 도구는 서브포켓을 만들지 않습니다. 업비트 앱에서 서브포켓(최대 5개)을 먼저 만들어 주세요.

### 3. 설치

`setup.bat`을 실행하면 가상환경 생성과 패키지 설치가 한 번에 끝납니다.
수동으로 하려면:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. 환경 설정

`setup.bat`이 `.env.example`을 `.env`로 복사해 줍니다. 값을 채워 넣으세요.
`.env`는 `.gitignore`에 등록되어 있어 git에 커밋되지 않습니다.

```
UPBIT_OPEN_API_ACCESS_KEY=발급받은 Access Key
UPBIT_OPEN_API_SECRET_KEY=발급받은 Secret Key
```

환경변수로 직접 지정해도 됩니다(우선순위: 환경변수 > `.env`).

```powershell
$env:UPBIT_OPEN_API_ACCESS_KEY="..."
$env:UPBIT_OPEN_API_SECRET_KEY="..."
.\.venv\Scripts\python.exe web.py
```

영구 등록하면 키가 디스크에 남지 않습니다.

```powershell
[Environment]::SetEnvironmentVariable("UPBIT_OPEN_API_ACCESS_KEY", "발급받은 Key", "User")
[Environment]::SetEnvironmentVariable("UPBIT_OPEN_API_SECRET_KEY", "발급받은 Key", "User")
```

## 웹 UI 옵션

`run_web.bat`은 인자를 받지 않으므로, 포트 등 옵션을 쓰려면 파이썬을 직접 실행하세요.

```powershell
.\.venv\Scripts\python.exe web.py --port 8080        # 포트 변경 (기본 5000)
.\.venv\Scripts\python.exe web.py --no-browser       # 브라우저 자동 실행 안 함
.\.venv\Scripts\python.exe web.py --env-file .env.local
```

기본 바인딩은 `127.0.0.1`이라 **내 PC에서만** 접속됩니다.
다른 기기에서 열고 싶다면 `--host 0.0.0.0`을 쓰되, 실제 자산 이동 도구라 신중해야 합니다.

## 사용법 (터미널)

연결과 권한부터 확인합니다.

```bash
python main.py check
```

포켓별 자산 현황을 봅니다.

```bash
python main.py status
```

```
[메인포켓 (메인포켓)]  uuid=9ca023a5-...
자산            수량        잠김  매수평균가          현재가(KRW)      평가금액(KRW)
KRW 원화      1,250,000          -  -                    1            1,250,000
BTC 비트코인     0.15          -  92,000,000 KRW      140,000,000       21,000,000
  소계 22,250,000 KRW

[단기 트레이딩 (서브포켓)]  uuid=...
KRW 원화        300,000          -  -                    1              300,000
  소계 300,000 KRW

합계 22,550,000 KRW
```

### 자산 이동 (터미널)

`move`는 출발 포켓 → 도착 포켓 → 자산 → 수량을 순서대로 물어봅니다.
수량에 `all`(또는 빈 입력)을 넣으면 가용 잔고 전량을 옮깁니다.

```bash
python main.py move
```

**기본값은 드라이런입니다.** 계획만 출력하고 API를 호출하지 않습니다.

```bash
python main.py move --execute      # 계획 확인 후 실제 이전
python main.py move-all            # 자산 전체 이동 (드라이런)
python main.py move-all --execute  # 자산 전체 이동 (실행)
```

잠긴(`locked`) 자산은 기본적으로 제외되며, `move-all`에서 여부를 물어봅니다.
`--execute`를 주면 확인 프롬프트가 생략되므로 신중히 사용하세요.

### 이전 내역 (터미널)

```bash
python main.py history
python main.py history --limit 50
python main.py history --currency BTC
python main.py history --states done,failed
python main.py history --from-pocket 메인포켓 --to-pocket 단기
```

포켓은 **이름**, **UUID**, **UUID 앞 8자리**로 지정할 수 있습니다.

## 사용한 API

| 용도 | 엔드포인트 | 필요 권한 |
| --- | --- | --- |
| 포켓 목록 | `GET /v1/pockets` | 포켓관리 |
| 메인포켓 잔고 | `GET /v1/accounts` | 자산조회 |
| 서브포켓 잔고 | `GET /v1/pockets/assets?uuid=` | 포켓관리 |
| 포켓 간 자산 이전 | `POST /v1/pockets/universal_transfers` | 포켓관리 |
| 이전 내역 | `GET /v1/pockets/universal_transfers` | 포켓관리 |
| 시세 (KRW 마켓) | `GET /v1/market/all`, `GET /v1/ticker` | 없음 (공개 API) |

인증은 업비트 규격대로 `HS512` JWT에 `query_hash`(SHA512)를 넣어 생성합니다.

## 안전장치

웹 UI와 CLI 양쪽 모두 다음을 지킵니다.

* **계획 → 확인 → 실행** 2단계. 계획 조회(`POST /api/plan`)는 실제 요청을 보내지 않으며,
  실행(`POST /api/transfer`)은 `confirmed` 플래그와 브라우저 확인 창을 모두 요구합니다.
* 실행 시점에 잔고를 **다시 조회해 재검증**합니다. 계획 이후 잔고가 줄었으면 차단됩니다.
* CSRF 토큰으로 POST 요청을 보호합니다.
* `from == to` 이전, 0 이하 수량, 가용 잔고 초과 요청을 전송 전에 차단합니다.
* 잠긴 잔고(`locked`)는 자동으로 제외됩니다.
* 모든 이전 요청에 고유 `identifier`를 붙여 중복 실행을 방지합니다.
* 응답 상태(`submitted` / `processing` / `done` / `failed`)는 `/history`에서 확인합니다.
* HTML 응답에 `Cache-Control: no-store`를 붙여 자산 정보가 캐시에 남지 않게 합니다.
* 서버는 `127.0.0.1`에만 바인딩됩니다.

## 구조

```
setup.bat                  최초 1회 설정 (가상환경 + 패키지 + .env)
run_web.bat                웹 UI 실행
run_cli.bat                터미널 실행 (인자 전달)
main.py                    터미널 CLI 진입점
web.py                     웹 UI 진입점 (Flask)
upbit_pocket/
  config.py                API Key 로딩 (환경변수 > .env)
  auth.py                  JWT(query_hash) 생성
  client.py                REST 호출, 레이트리밋, 에러 처리
  models.py                Pocket / Balance / Transfer 등 도메인 모델
  pricing.py               통화별 원화 시세 (KRW 마켓 → BTC 경유)
  service.py               포켓 조회·이전 계획·실행 로직 (웹/CLI 공용)
  cli.py                   터미널 명령/대화형 인터페이스
  display.py / views.py    터미널 테이블 렌더링
  web/
    app.py                 Flask 앱 팩토리
    routes.py              대시보드 / 내역 / plan·transfer API
    forms.py               폼 값 검증
    templates/             base · dashboard · history · error
    static/app.css         다크 테마 스타일
tests/
  test_pocket.py           도메인 로직 20개
  test_web.py              웹 라우트 18개 (CSRF·재검증 포함)
.venv/                     가상환경 (git에 커밋되지 않음)
```

## 테스트

`pytest`는 개발용 의존성이므로 `requirements-dev.txt`에 있습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
```

## 개발 메모

* `.bat` 파일은 **ASCII만 사용**합니다. `cmd.exe`가 코드페이지(CP949 등)로 파일을 읽기 때문에
  UTF-8로 저장된 한글 주석이 들어가면 스크립트 자체가 깨집니다. 한글 안내는 Python이 출력합니다.
* 배치 안에서 `&&` / `||` 로 괄호 묶은 명령을 잇는 문법은 피합니다 (`goto` + 라벨을 씁니다).
* 가상환경을 지우고 다시 만들려면 `.venv` 폴더만 삭제하면 됩니다. 그다음 `setup.bat`.

## 주의

* 이 도구는 자산을 실제로 이동시킵니다. `--execute` 사용 전 반드시 드라이런 결과로 계획을 확인하세요.
* 업비트 API Key는 외부에 노출되지 않도록 보관하고, 저장소에 커밋하지 마세요.
