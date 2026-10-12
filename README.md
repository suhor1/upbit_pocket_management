# 업비트 포켓(Pocket) 관리 도구

업비트 공식 API를 이용해 **메인포켓 / 서브포켓**의 자산을 조회하고,
포켓 간 자산 이동을 수행하는 도구입니다.

브라우저에서 쓰는 **웹 UI**(`web.py`)와 터미널에서 쓰는 **CLI**(`main.py`) 두 가지 진입점을 제공합니다.

## 빠른 시작 (웹 UI)

```bash
pip install -r requirements.txt
copy .env.example .env          # Access Key / Secret Key 입력
python web.py                   # http://127.0.0.1:5000 자동 실행
```

| 페이지 | 경로 | 설명 |
| --- | --- | --- |
| 대시보드 | `/` | 포켓별 자산 현황, 시세 평가, 자산 이동 |
| 이전 내역 | `/history` | 포켓 간 이전 기록 조회 (자산·상태 필터) |

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

## 준비 사항

### 1. API Key 발급

[업비트 API Key 관리](https://upbit.com/mypage/open_api_management)에서 발급받습니다.

* **포켓 관리 권한이 반드시 필요합니다.** ([포켓 관리](https://docs.upbit.com/kr/reference/pocket-overview) 권한은 메인포켓에서만 발급 가능)
* 조회만 할 거라면 `[자산조회]` + `[포켓관리]`면 충분합니다.
* 발급한 Key의 **호출 IP 목록**에 현재 PC의 IP를 등록해야 합니다.

### 2. 서브포켓 생성

이 도구는 서브포켓을 만들지 않습니다. 업비트 앱에서 서브포켓(최대 5개)을 먼저 만들어 주세요.

### 3. 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 설정

`.env.example`을 `.env`으로 복사하고 값을 입력합니다. `.env`는 git에 커밋되지 않습니다.

```
UPBIT_OPEN_API_ACCESS_KEY=발급받은 Access Key
UPBIT_OPEN_API_SECRET_KEY=발급받은 Secret Key
```

환경변수로 직접 지정해도 됩니다(우선순위: 환경변수 > `.env`).

```powershell
$env:UPBIT_OPEN_API_ACCESS_KEY="..."
$env:UPBIT_OPEN_API_SECRET_KEY="..."
python web.py
```

영구 등록하면 키가 디스크에 남지 않습니다.

```powershell
[Environment]::SetEnvironmentVariable("UPBIT_OPEN_API_ACCESS_KEY", "발급받은 Key", "User")
[Environment]::SetEnvironmentVariable("UPBIT_OPEN_API_SECRET_KEY", "발급받은 Key", "User")
```

## 웹 UI 옵션

```bash
python web.py --port 8080        # 포트 변경 (기본 5000)
python web.py --no-browser       # 브라우저 자동 실행 안 함
python web.py --env-file .env.local
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
```

## 테스트

```bash
python -m pytest tests -q
```

## 주의

* 이 도구는 자산을 실제로 이동시킵니다. `--execute` 사용 전 반드시 드라이런 결과로 계획을 확인하세요.
* 업비트 API Key는 외부에 노출되지 않도록 보관하고, 저장소에 커밋하지 마세요.
