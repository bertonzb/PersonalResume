# =============================================================================
# 文件：app/schemas/auth.py
# 作用：定义认证/鉴权相关的请求和响应数据结构（Pydantic Schema）。
# 解释：Schema 是 Pydantic 数据模型，负责：
#       1. 定义 API 接口的输入输出格式（请求体、响应体）。
#       2. 自动校验数据（比如邮箱格式、密码长度）。
#       3. 生成 API 文档（FastAPI 会自动读取这些模型，生成 Swagger 文档）。
#       它们与 ORM 模型（models/）不同：ORM 模型对应数据库表，
#       Schema 对应 API 的 JSON 数据。
# =============================================================================

# 延迟求值的类型注解。
from __future__ import annotations

# ---- 导入 Pydantic 的核心类 ----
# BaseModel：Pydantic 的基类，所有数据校验模型都继承它。
#   Pydantic BaseModel 和 SQLAlchemy Base 是两个完全不同的东西：
#   Pydantic BaseModel 用于数据校验和序列化（JSON），
#   SQLAlchemy Base 用于数据库 ORM 映射。
# EmailStr：特殊的字符串类型，Pydantic 会自动校验值是否是合法的邮箱格式。
# Field：用于给字段添加额外的元数据（描述、校验规则、默认值等）。
from pydantic import BaseModel, EmailStr, Field


# ---- 注册请求 ----

class RegisterRequest(BaseModel):
    # email：注册时用户填写的邮箱。
    #   Field(...)：...（Ellipsis）在 Pydantic 中表示必填。
    #   min_length=5：至少有 5 个字符（a@b.c 是最短的合法邮箱，5 个字符）。
    #   max_length=255：最多 255 个字符（对应数据库 VARCHAR(255)）。
    #   注意：这里用的是 str 而不是 EmailStr，
    #   因为开发阶段 EmailStr 需要额外安装 email-validator 依赖。
    email: str = Field(..., min_length=5, max_length=255)

    # password：注册时用户填写的密码。
    #   min_length=8：密码至少 8 位，这是安全底线。
    #   max_length=128：密码最多 128 位（太长的密码没必要，而且可能被用于攻击）。
    password: str = Field(..., min_length=8, max_length=128)


# ---- 登录请求 ----

class LoginRequest(BaseModel):
    # email：登录时填写的邮箱（作为账号）。
    #   和注册不同，登录时不做长度校验——只要不为空就行。
    email: str

    # password：登录时填写的密码。
    password: str


# ---- 登录成功后返回的 Token ----

class TokenResponse(BaseModel):
    # access_token：JWT 访问令牌，是一串加密的字符串。
    #   前端拿到这个 token 后，在后续请求的 Authorization 头中带上它，
    #   后端通过解析 token 来确认你是谁。
    access_token: str

    # token_type：令牌类型，标准值通常是 bearer。
    #   Bearer Token 是 OAuth 2.0 的标准：持有这个 token 的人（bearer）
    #   就拥有对应的权限，像持有门票一样。
    token_type: str = "bearer"


# ---- 用户信息响应 ----

class UserResponse(BaseModel):
    # id：用户唯一标识（UUID 格式的字符串，如 a1b2c3d4-...）。
    #   注意这里用的是 str 而不是 UUID 类型，
    #   因为 API 返回的 JSON 中 ID 以字符串形式呈现。
    id: str

    # email：用户的邮箱地址。
    email: str

    # role：用户角色（user 或 admin）。
    role: str

    # is_active：账号是否激活。
    is_active: bool
