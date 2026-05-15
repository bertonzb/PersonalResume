# =============================================================================
# 文件：app/models/user.py
# 作用：定义用户（User）的数据库 ORM 模型。
# 解释：User 代表系统的注册用户。每个用户可以拥有多个文档，可以发起对话。
#       注意密码存储的是哈希后的值（hashed_password），绝不存储明文密码。
# =============================================================================

# 延迟求值的类型注解。
from __future__ import annotations

# ---- 导入 SQLAlchemy 的列类型 ----
# Boolean：布尔类型（True / False），映射到数据库的 BOOLEAN。
# String： 变长字符串类型，括号里是最大长度。
from sqlalchemy import Boolean, String

# Mapped：声明式类型标注，告诉 SQLAlchemy 这一列存什么 Python 类型。
# mapped_column：定义数据库列的详细属性（主键、唯一、默认值等）。
from sqlalchemy.orm import Mapped, mapped_column

# 导入父类 BaseModel，User 会自动继承 id、created_at、updated_at 字段。
from app.models.base import BaseModel


# ---- User 模型 ----
class User(BaseModel):
    # __tablename__：指定数据库表名为 users（复数形式），
    #   符合数据库命名惯例（表名用复数）。
    __tablename__ = "users"

    # email：用户的电子邮箱地址，同时也是登录时的账号。
    #   String(255)：VARCHAR(255)，最多 255 个字符。
    #   unique=True：数据库唯一约束，保证不会有两条记录使用同一个邮箱。
    #   index=True：为邮箱列创建索引，登录时按邮箱查询用户速度更快。
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # hashed_password：用户密码经过哈希（加密）处理后的字符串。
    #   为什么不存明文密码？因为如果数据库被泄露，攻击者无法直接用哈希值登录。
    #   哈希是一种单向加密：从 password 算出哈希值很容易，
    #   但从哈希值反推 password 几乎不可能。
    #   String(255)：预留足够长度，因为哈希算法（如 bcrypt）输出的字符串较长。
    hashed_password: Mapped[str] = mapped_column(String(255))

    # is_active：用户账号是否处于激活状态。
    #   Boolean：数据库列类型为 BOOLEAN。
    #   default=True：新注册的用户默认是激活状态。
    #   管理员可以把某个用户的 is_active 设为 False 来禁用该账号。
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # role：用户的角色/权限级别。
    #   String(20)：最多 20 个字符。
    #   default=user：新注册用户默认是普通用户。
    #   可选值：
    #     - user：  普通用户，只能管理自己的文档和对话。
    #     - admin： 管理员，可以管理所有用户和文档。
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | admin
