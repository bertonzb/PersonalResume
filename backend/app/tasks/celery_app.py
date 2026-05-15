# =============================================================================
# 文件：app/tasks/celery_app.py
# 作用：Celery 异步任务队列的配置和实例创建。
#       Celery = 后台处理耗时任务，不阻塞用户的 HTTP 请求。
#       类比：餐厅点单后前台立刻回"已下单"，厨房（Celery Worker）在后台做菜。
# =============================================================================
from __future__ import annotations
# Celery：Python 最流行的异步任务队列框架
from celery import Celery
from app.config import get_settings

# 获取全局配置单例
settings = get_settings()

# ---- 创建 Celery 应用实例 ----
# "deepscribe"：应用名称，用于日志和监控
# broker=redis_url：消息代理用 Redis，任务先存入 Redis，Worker 再领取
# backend=redis_url：结果后端也用 Redis，Worker 执行完后结果存回 Redis
celery_app = Celery(
    "deepscribe",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# ---- Celery 全局配置 ----
celery_app.conf.update(
    # JSON 序列化（比 pickle 更安全，防注入攻击）
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 时区：上海（UTC+8），定时任务按北京时间执行
    timezone="Asia/Shanghai",
    enable_utc=True,           # 内部统一用 UTC 存储
    task_track_started=True,   # 追踪 STARTED 状态，前端可以看进度
    # soft_time_limit=600：软超时 10 分钟（超时抛异常，可捕获）
    # time_limit=900：硬超时 15 分钟（超时直接杀进程，不可捕获）
    task_soft_time_limit=600,
    task_time_limit=900,
    # 自动发现 tasks 模块中的任务
    imports=("app.tasks.jobs",),
    # ---- Celery Beat 定时调度 ----
    beat_schedule={
        "weekly-report-monday-9am": {
            "task": "deep_research",                          # 要执行的任务
            "schedule": 0.0,                                  # 60 秒一次（开发调试用）
            # 生产环境改为：crontab(hour=9, minute=0, day_of_week=1) 即每周一 9:00
            "args": ("system", "weekly_report"),              # 传给任务的参数
        },
    },
)
