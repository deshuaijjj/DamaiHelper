"""
任务调度器
负责管理和调度抢票任务
"""
import asyncio
import uuid
import logging
import threading  # 【关键问题4修复】导入 threading 用于 Event
from dataclasses import dataclass, field
from datetime import datetime, timezone  # 【BUG修复2】导入 timezone 用于时区处理
from typing import Optional, Dict, List, Callable, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# 数据模型
# ══════════════════════════════════════════════════════════════════

class TicketTaskRequest(BaseModel):
    """API 请求模型，用于接收前端 HTTP 请求"""
    event_url: str                        # 演出详情页 URL / 深链接
    device_ids: List[str]                 # 参与抢票的设备 ID 列表
    start_time: Optional[str] = None      # 定时开抢时间，ISO 格式字符串，None 表示立即执行
    platform: str = "android"             # "android" 或 "ios"
    # 【BUG-S1修复】添加抢票业务参数
    preferred_area: Optional[str] = None  # 优先票档区域
    target_price: Optional[int] = None    # 目标价格上限
    quantity: int = 1                     # 购票数量
    buyer_name: Optional[str] = None      # 购票人姓名


@dataclass
class TaskState:
    """任务内部状态，用于调度器内部管理"""
    task_id: str
    event_url: str
    device_ids: List[str]
    start_time: Optional[str]
    platform: str
    status: str = "pending"               # pending / running / success / failed / cancelled
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    asyncio_task: Optional[Any] = field(default=None, repr=False)  # asyncio.Task 对象
    # 【BUG-S1修复】添加抢票业务参数字段
    preferred_area: Optional[str] = None  # 优先票档区域
    target_price: Optional[int] = None    # 目标价格上限
    quantity: int = 1                     # 购票数量
    buyer_name: Optional[str] = None      # 购票人姓名
    # 【关键问题4修复】添加 stop_event 用于任务取消
    stop_event: Optional[threading.Event] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        """序列化为可 JSON 化的字典（不含 asyncio_task）"""
        return {
            "task_id": self.task_id,
            "event_url": self.event_url,
            "device_ids": self.device_ids,
            "start_time": self.start_time,
            "platform": self.platform,
            "status": self.status,
            "created_at": self.created_at,
            "preferred_area": self.preferred_area,
            "target_price": self.target_price,
            "quantity": self.quantity,
            "buyer_name": self.buyer_name,
        }


# ══════════════════════════════════════════════════════════════════
# 任务调度器
# ══════════════════════════════════════════════════════════════════

class TaskScheduler:
    """任务调度器，负责管理和调度抢票任务"""
    
    def __init__(self, device_manager, broadcast_callback: Optional[Callable] = None):
        self.device_manager = device_manager
        self.tasks: Dict[str, TaskState] = {}
        self.broadcast_callback = broadcast_callback  # WebSocket 广播回调
    
    async def create_task(self, request: TicketTaskRequest) -> TaskState:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        task_state = TaskState(
            task_id=task_id,
            event_url=request.event_url,
            device_ids=request.device_ids,
            start_time=request.start_time,
            platform=request.platform,
            # 【BUG-S1修复】传递业务参数
            preferred_area=request.preferred_area,
            target_price=request.target_price,
            quantity=request.quantity,
            buyer_name=request.buyer_name,
            # 【关键问题4修复】为每个任务创建 stop_event
            stop_event=threading.Event(),
        )
        self.tasks[task_id] = task_state
        logger.info(f"任务已创建: {task_id}")
        return task_state
    
    async def start_task(self, task_id: str) -> bool:
        """启动任务"""
        task_state = self.tasks.get(task_id)
        if not task_state:
            logger.error(f"任务不存在: {task_id}")
            return False
        if task_state.status == "running":
            logger.warning(f"任务已在运行: {task_id}")
            return False

        # 【代码质量20】初始状态设为 pending，等待开始时间
        task_state.status = "pending"
        await self._notify(task_id)

        # 创建 asyncio 协程任务（非阻塞，立即返回）
        asyncio_task = asyncio.create_task(self._run_task(task_id))
        task_state.asyncio_task = asyncio_task

        # 任务结束后自动清理 asyncio_task 引用
        def _on_done(fut):
            task_state.asyncio_task = None
        asyncio_task.add_done_callback(_on_done)

        logger.info(f"任务已启动: {task_id}")
        return True
    
    async def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        task_state = self.tasks.get(task_id)
        if not task_state:
            return False
        
        # 【关键问题4修复】触发 stop_event，通知任务停止
        if task_state.stop_event:
            task_state.stop_event.set()
        
        if task_state.asyncio_task and not task_state.asyncio_task.done():
            task_state.asyncio_task.cancel()
            try:
                await task_state.asyncio_task   # 等待取消完成
            except asyncio.CancelledError:
                pass                            # 正常，取消成功
        task_state.status = "cancelled"
        task_state.asyncio_task = None
        await self._notify(task_id)
        logger.info(f"任务已停止: {task_id}")
        return True
    
    async def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        await self.stop_task(task_id)           # 先停止（如果在运行）
        removed = self.tasks.pop(task_id, None)
        if removed:
            logger.info(f"任务已删除: {task_id}")
        return removed is not None
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """获取单个任务信息"""
        task_state = self.tasks.get(task_id)
        return task_state.to_dict() if task_state else None
    
    def get_all_tasks(self) -> List[dict]:
        """获取所有任务信息"""
        return [ts.to_dict() for ts in self.tasks.values()]
    
    async def _run_task(self, task_id: str):
        """核心调度方法，执行任务"""
        task_state = self.tasks[task_id]
        try:
            # ── 步骤1：定时等待 ──
            if task_state.start_time:
                try:
                    # 【BUG修复2】统一使用 UTC 时区，避免时区不匹配导致的 TypeError
                    target = datetime.fromisoformat(task_state.start_time)
                    # 如果 target 没有时区信息，假定为 UTC
                    if target.tzinfo is None:
                        target = target.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    wait_seconds = (target - now).total_seconds()
                    if wait_seconds > 0:
                        logger.info(f"任务 {task_id} 将在 {wait_seconds:.1f} 秒后开始")
                        await asyncio.sleep(wait_seconds)
                except ValueError:
                    logger.warning(f"start_time 格式无效，立即执行: {task_state.start_time}")

            # ── 步骤2：并发对所有设备执行抢票 ──
            # 【代码质量20】等待结束后，真正开始抢票前设置状态为 running
            task_state.status = "running"
            await self._notify(task_id)

            results = await asyncio.gather(
                *[self._rush_ticket(task_state, device_id)
                  for device_id in task_state.device_ids],
                return_exceptions=True
            )

            # ── 步骤3：判断结果 ──
            if any(r is True for r in results):
                task_state.status = "success"
                logger.info(f"任务 {task_id} 执行成功")
            else:
                task_state.status = "failed"
                logger.warning(f"任务 {task_id} 执行失败")

        except asyncio.CancelledError:
            task_state.status = "cancelled"
            logger.info(f"任务 {task_id} 已取消")
            raise   # 必须重新抛出，让 asyncio 知道任务被取消
        except Exception as e:
            logger.error(f"任务 {task_id} 异常: {e}", exc_info=True)
            task_state.status = "failed"
        finally:
            await self._notify(task_id)   # 无论成功/失败/取消，都推送最终状态
    
    async def _rush_ticket(self, task_state: TaskState, device_id: str) -> bool:
        """单设备抢票方法，加入重试机制"""
        MAX_RETRIES = 5
        RETRY_INTERVAL = 0.3   # 秒

        # 【BUG修复3】添加 await 调用异步方法
        driver = await self.device_manager.get_device_by_platform(device_id, task_state.platform)

        if driver is None:
            logger.error(f"设备 {device_id} 未连接或不存在")
            return False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # 【BUG-S1修复】传递完整的业务参数
                # 【BUG-S2修复】超时从 30 秒改为 300 秒（5分钟）
                # 【关键问题4修复】传递 stop_event 用于任务取消
                result = await asyncio.wait_for(
                    driver.rush_ticket(
                        event_url=task_state.event_url,
                        preferred_area=task_state.preferred_area,
                        target_price=task_state.target_price,
                        quantity=task_state.quantity,
                        buyer_name=task_state.buyer_name,
                        stop_event=task_state.stop_event,
                    ),
                    timeout=300  # 5分钟超时
                )
                if result:
                    logger.info(f"设备 {device_id} 第{attempt}次尝试抢票成功")
                    return True
                logger.warning(f"设备 {device_id} 第{attempt}次抢票未成功，重试中...")
            except asyncio.TimeoutError:
                logger.warning(f"设备 {device_id} 第{attempt}次抢票超时（300秒）")
            except asyncio.CancelledError:
                raise   # 任务被取消时必须传播
            except Exception as e:
                logger.warning(f"设备 {device_id} 第{attempt}次抢票异常: {e}")

            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_INTERVAL)

        logger.error(f"设备 {device_id} 已达最大重试次数，抢票失败")
        return False
    
    async def _notify(self, task_id: str):
        """当任务状态变更时，通过 WebSocket 广播最新状态"""
        if not self.broadcast_callback:
            return
        task_state = self.tasks.get(task_id)
        if not task_state:
            return
        try:
            await self.broadcast_callback({
                "type": "task_update",
                "data": task_state.to_dict()
            })
        except Exception as e:
            logger.warning(f"状态推送失败: {e}")


