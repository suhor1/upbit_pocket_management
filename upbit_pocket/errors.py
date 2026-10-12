class UpbitPocketError(Exception):
    """프로그램 전체에서 사용하는 최상위 예외."""


class ConfigError(UpbitPocketError):
    """API Key 등 설정값이 올바르지 않을 때."""


class UpbitAPIError(UpbitPocketError):
    """업비트 API가 오류 응답을 반환했을 때."""

    def __init__(self, code: str, message: str, status_code: int | None = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.status_code = status_code


class TransferValidationError(UpbitPocketError):
    """자산 이전 요청이 로컬 검증 단계에서 거부되었을 때."""


class TransferAborted(UpbitPocketError):
    """사용자가 자산 이전을 취소했을 때."""
