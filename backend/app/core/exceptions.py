# 启用"延迟求值"类型注解
from __future__ import annotations


# ---- 自定义异常体系 ----
# 为什么不用 Python 内置的 Exception？
# 因为我们想让每个错误带上"错误码"（code），方便前端根据 code 做不同处理
# 同时全局异常处理器（在 main.py 里）可以统一捕获这些异常，返回标准格式的错误

# ========== 业务异常基类 ==========
# 所有自定义异常的"父类"
# 继承 Python 内置的 Exception，增加了 code 属性
class AppException(Exception):
    """业务异常基类。"""

    # message：错误描述文字
    # code：错误码（如 NOT_FOUND、PERMISSION_DENIED）
    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        # super().__init__(message)：调用父类 Exception 的构造方法
        super().__init__(message)
        # 把参数存为实例属性，方便异常处理器读取
        self.message = message
        self.code = code


# ========== 资源未找到异常 ==========
# 例如：文档 ID 不存在、用户不存在时抛出
class NotFoundError(AppException):
    # resource：资源类型名称（如 "document"、"user"）
    # resource_id：具体的资源 ID
    def __init__(self, resource: str, resource_id: str) -> None:
        # 调用父类构造方法，自动生成错误消息和错误码
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            code="NOT_FOUND",
        )


# ========== 权限拒绝异常 ==========
# 例如：未登录、无权限访问时抛出
class PermissionDeniedError(AppException):
    def __init__(self) -> None:
        super().__init__(message="Permission denied", code="PERMISSION_DENIED")
