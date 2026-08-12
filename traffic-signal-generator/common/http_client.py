import requests
import random
import time

from common.common_vars import DEFAULT_TIMEOUT
from utils.logger import log


# evaluator 单次 HTTP 请求超时时间，单位秒。
EVALUATOR_HTTP_TIMEOUT_SECONDS = 30.0

# evaluator 繁忙或网络抖动时的最大重试次数。
EVALUATOR_RETRY_TIMES = 12

# 首次重试前的基础等待时间，单位秒；后续会按指数退避放大。
EVALUATOR_RETRY_DELAY_SECONDS = 1.0

# 单次重试等待时间上限，单位秒，避免退避时间无限增长。
EVALUATOR_RETRY_MAX_DELAY_SECONDS = 8.0

# 单个 generator 实例同时发往 evaluator 的最大并发请求数。
EVALUATOR_MAX_INFLIGHT = 4

# GA 外层等待单个评估任务完成的超时预算，
# 需要覆盖「HTTP 超时 * 重试次数 + 退避等待 + 额外缓冲」。
GA_EVALUATION_TIMEOUT_SECONDS = max(
    DEFAULT_TIMEOUT,
    int(
        EVALUATOR_HTTP_TIMEOUT_SECONDS * EVALUATOR_RETRY_TIMES
        + EVALUATOR_RETRY_MAX_DELAY_SECONDS * max(EVALUATOR_RETRY_TIMES - 1, 0)
        + 10
    ),
)

# 这些状态码通常表示服务暂时繁忙或网关瞬时异常，适合等待后重试。
DEFAULT_RETRY_STATUS_CODES = (429, 502, 503, 504)


class HttpServiceClient:
    """HTTP 服务调用客户端"""

    def __init__(
        self,
        base_url,
        timeout=EVALUATOR_HTTP_TIMEOUT_SECONDS,
        retry_times=EVALUATOR_RETRY_TIMES,
        retry_delay_seconds=EVALUATOR_RETRY_DELAY_SECONDS,
        max_retry_delay_seconds=EVALUATOR_RETRY_MAX_DELAY_SECONDS,
        retry_status_codes=None,
    ):
        # 统一在客户端内部使用 evaluator 的固定默认超时和重试参数，
        # 这样调用方只需传 base_url，避免在业务代码里散落同一套配置。
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_times = retry_times
        self.retry_delay_seconds = retry_delay_seconds
        self.max_retry_delay_seconds = max_retry_delay_seconds
        self.retry_status_codes = set(retry_status_codes or DEFAULT_RETRY_STATUS_CODES)
        self.session = None

    def _get_retry_delay(self, attempt, response=None):
        # 如果服务端显式返回 Retry-After，则优先尊重服务端的等待时间。
        if response is not None:
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    return max(0.0, float(retry_after))
                except (TypeError, ValueError):
                    pass

        # 否则使用指数退避，并附加少量随机抖动，
        # 避免多个并发请求在同一时刻再次冲击下游服务。
        base_delay = min(
            self.max_retry_delay_seconds,
            self.retry_delay_seconds * (2 ** attempt),
        )
        jitter = min(1.0, base_delay * 0.2)
        return base_delay + random.uniform(0, jitter)

    def __enter__(self):
        """建立连接"""
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'HttpServiceClient/1.0'
        })
        return self

    def post(self, endpoint, data=None):
        """POST 请求"""
        url = f"{self.base_url}{endpoint}"

        # 在有限次数内重试，尽量把 evaluator 的瞬时繁忙转化为等待而不是直接失败。
        for attempt in range(self.retry_times):
            try:
                response = self.session.post(
                    url=url,
                    json=data,
                    timeout=self.timeout
                )

                # 对明确可重试的繁忙/网关类状态码走退避重试。
                if response.status_code in self.retry_status_codes and attempt < self.retry_times - 1:
                    delay = self._get_retry_delay(attempt, response=response)
                    response_text = (response.text or '')[:4000]
                    log.warning(
                        f"请求繁忙，准备重试 (尝试 {attempt + 1}/{self.retry_times}): "
                        f"status={response.status_code}, url={url}, delay={delay:.2f}s, body={response_text}"
                    )
                    time.sleep(delay)
                    continue

                # 非重试状态码或最后一次尝试时，按正常 HTTP 结果处理。
                response.raise_for_status()
                result = response.json()
                return result

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else 'unknown'
                response_text = ''
                if e.response is not None:
                    response_text = (e.response.text or '')[:4000]
                log.info(
                    f"请求失败 (尝试 {attempt + 1}/{self.retry_times}): status={status_code}, url={url}, body={response_text}"
                )
                if attempt == self.retry_times - 1:
                    return {
                        'error': 'http_error',
                        'status_code': status_code,
                        'url': url,
                        'response_text': response_text,
                    }
                # 对 HTTP 层错误继续退避，给下游一点恢复时间。
                delay = self._get_retry_delay(attempt, response=e.response)
                time.sleep(delay)
            except requests.exceptions.RequestException as e:
                log.info(f"请求失败 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                if attempt == self.retry_times - 1:
                    return {
                        'error': 'request_exception',
                        'exception': str(e),
                        'url': url,
                    }
                # 网络抖动、连接超时等异常也做同样的退避重试。
                delay = self._get_retry_delay(attempt)
                time.sleep(delay)
        return {
            'error': 'request_failed',
            'url': url,
        }

    def __exit__(self, exc_type, exc_val, exc_tb):
        """关闭会话"""
        self.session.close()
