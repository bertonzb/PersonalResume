# 启用"延迟求值"类型注解
from __future__ import annotations

# logging：Python 标准库的日志模块
import logging
# sys：系统相关，这里用于指定日志输出到 stdout（控制台）
import sys

# structlog：第三方结构化日志库
# 普通日志输出："用户 zhangsan 上传了文件"
# 结构化日志输出：{"event":"upload","user":"zhangsan","file":"test.pdf"}
# 结构化日志的优点：方便用工具搜索、分析、统计
import structlog


# ---- 日志初始化函数 ----
# 在应用启动时调用一次，配置全局的日志格式和处理流程
def setup_logging() -> None:
    """配置 structlog 结构化日志输出。"""

    # TimeStamper：给每条日志添加时间戳
    # fmt="iso" 表示使用 ISO 8601 格式（如 2026-05-13T09:30:00Z）
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    # structlog.configure()：全局配置，设置日志的处理"流水线"
    # 每条日志会依次经过下面的 processors 列表处理
    structlog.configure(
        processors=[
            # ① 合并上下文变量（比如自动注入的 trace_id、user_id）
            structlog.contextvars.merge_contextvars,
            # ② 添加日志级别（info / warning / error）
            structlog.stdlib.add_log_level,
            # ③ 格式化 %s 占位符参数
            structlog.stdlib.PositionalArgumentsFormatter(),
            # ④ 添加时间戳
            timestamper,
            # ⑤ 添加调用堆栈信息（方便定位代码位置）
            structlog.processors.StackInfoRenderer(),
            # ⑥ 格式化异常信息
            structlog.processors.format_exc_info,
            # ⑦ 解码 Unicode 字符（避免乱码）
            structlog.processors.UnicodeDecoder(),
            # ⑧ 最终渲染为 JSON 格式输出
            structlog.processors.JSONRenderer(),
        ],
        # wrapper_class：使用 stdlib 兼容的日志包装器
        wrapper_class=structlog.stdlib.BoundLogger,
        # context_class：上下文变量存储方式（dict 字典）
        context_class=dict,
        # logger_factory：使用标准库兼容的日志工厂
        logger_factory=structlog.stdlib.LoggerFactory(),
        # cache_logger_on_first_use：第一次使用后缓存日志器，提高性能
        cache_logger_on_first_use=True,
    )

    # 同时配置 Python 标准库的 logging，输出到控制台（stdout）
    # 级别设为 INFO，意味着 DEBUG 级别的日志不会显示
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


# ---- 全局日志对象 ----
# 项目里所有文件都通过 import 这个 logger 来记录日志
# 用法：logger.info("upload_complete", file="test.pdf")
#       logger.error("upload_failed", error=str(e))
logger = structlog.get_logger()
