"""
FastAPI后端服务
提供REST API和WebSocket接口
"""
import asyncio
import json
import logging
import os
from typing import Optional, Set
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core.device_manager import DeviceManager
from core.scheduler import TaskScheduler, TicketTaskRequest

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化管理器
device_manager = DeviceManager()
task_scheduler = TaskScheduler(device_manager)

# WebSocket连接管理
active_connections: Set[WebSocket] = set()


async def broadcast(message: dict):
    """向所有已连接的 WebSocket 客户端广播消息"""
    if not active_connections:
        return
    data = json.dumps(message, ensure_ascii=False)
    disconnected = set()
    for ws in list(active_connections):
        try:
            await ws.send_text(data)
        except Exception as e:
            logger.warning(f"WebSocket 发送失败，将移除该连接: {e}")
            disconnected.add(ws)
    active_connections.difference_update(disconnected)


# 【代码质量16】使用 lifespan 替代已弃用的 @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    task_scheduler.broadcast_callback = broadcast
    logger.info("服务启动完成，WebSocket 广播已注册到调度器")
    yield
    # 关闭时执行（如需清理资源可在此添加）


# 初始化FastAPI
app = FastAPI(title="DamaiHelper API", version="1.0.0", lifespan=lifespan)

# 【BUG修复3】CORS 配置规范化：allow_credentials=True 时不能使用 allow_origins=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 请求体模型 ====================

class ConnectRequest(BaseModel):
    device_id: str
    platform: str                    # "android" 或 "ios"
    bundle_id: Optional[str] = None  # iOS 专用，Android 传 None 即可
    wda_port: int = 8100             # 【High-4补充】iOS WDA 端口


# ==================== API路由 ====================

@app.get("/")
async def root():
    return {"message": "DamaiHelper API is running"}


@app.get("/api/devices/scan")
async def scan_devices():
    """扫描所有设备"""
    android = await device_manager.scan_android_devices()
    ios = await device_manager.scan_ios_devices()
    return {
        "success": True,
        "android": android,
        "ios": ios,
    }


@app.post("/api/devices/connect")
async def connect_device(request: ConnectRequest):
    # 【High-4修复】将 bundle_id 和 wda_port 传递给 iOS 设备连接
    if request.platform == "android":
        result = await device_manager.connect_android_device(request.device_id)
    else:
        result = await device_manager.connect_ios_device(
            request.device_id,
            wda_port=request.wda_port,
            bundle_id=request.bundle_id
        )
    
    if result:
        return {"success": True, "message": f"设备 {request.device_id} 连接成功"}
    raise HTTPException(
        status_code=500,
        detail=f"设备 {request.device_id} 连接失败，请检查设备是否在线"
    )


@app.get("/api/devices")
async def get_devices():
    """获取所有已连接设备"""
    devices = await device_manager.get_all_devices()
    return {"success": True, "devices": devices}


@app.post("/api/devices/disconnect")
async def disconnect_device(device_id: str):
    result = await device_manager.disconnect_device(device_id)
    if result:
        return {"success": True, "message": f"设备 {device_id} 已断开连接"}
    raise HTTPException(
        status_code=404,
        detail=f"设备 {device_id} 不存在或未连接"
    )


@app.post("/api/devices/{device_id}/disconnect")
async def disconnect_device_by_path(device_id: str):
    """断开设备（路径参数版本，保持兼容）"""
    result = await device_manager.disconnect_device(device_id)
    if result:
        await broadcast({
            "type": "device_disconnected",
            "device_id": device_id
        })
        return {"success": True}
    raise HTTPException(
        status_code=404,
        detail=f"设备 {device_id} 不存在或未连接"
    )


@app.post("/api/tasks/create")
async def create_task(request: TicketTaskRequest):
    # 第一步：创建任务，写入调度器，返回 task_id
    task_state = await task_scheduler.create_task(request)
    # 第二步：立即启动任务（如果有 start_time，调度器内部会等待）
    await task_scheduler.start_task(task_state.task_id)
    return {
        "success": True,
        "task_id": task_state.task_id,
        "message": "任务已创建并开始调度",
    }


@app.post("/api/tasks")
async def create_task_legacy(request: TicketTaskRequest):
    """创建抢票任务（保持兼容旧路由）"""
    task_state = await task_scheduler.create_task(request)
    await task_scheduler.start_task(task_state.task_id)
    return {"success": True, "task_id": task_state.task_id}


@app.get("/api/tasks/list")
async def list_tasks():
    tasks = task_scheduler.get_all_tasks()   # 这个方法是同步的，不需要 await
    return {"success": True, "tasks": tasks}


@app.get("/api/tasks")
async def get_tasks():
    """获取所有任务（保持兼容旧路由）"""
    tasks = task_scheduler.get_all_tasks()
    return {"success": True, "tasks": tasks}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = task_scheduler.get_task(task_id)  # 同步方法，不需要 await
    if task:
        return {"success": True, "task": task}
    raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")


@app.post("/api/tasks/{task_id}/start")
async def start_task_by_path(task_id: str):
    """启动任务（路径参数版本，保持兼容）"""
    result = await task_scheduler.start_task(task_id)
    if result:
        await broadcast({
            "type": "task_started",
            "task_id": task_id
        })
        return {"success": True}
    raise HTTPException(
        status_code=404,
        detail=f"任务 {task_id} 不存在或已在运行"
    )


@app.post("/api/tasks/stop")
async def stop_task(task_id: str):
    result = await task_scheduler.stop_task(task_id)
    if result:
        return {"success": True, "message": f"任务 {task_id} 已停止"}
    raise HTTPException(
        status_code=404,
        detail=f"任务 {task_id} 不存在或已结束"
    )


@app.post("/api/tasks/{task_id}/stop")
async def stop_task_by_path(task_id: str):
    """停止任务（路径参数版本，保持兼容）"""
    result = await task_scheduler.stop_task(task_id)
    if result:
        await broadcast({
            "type": "task_stopped",
            "task_id": task_id
        })
        return {"success": True}
    raise HTTPException(
        status_code=404,
        detail=f"任务 {task_id} 不存在或已结束"
    )


@app.post("/api/tasks/remove")
async def remove_task(task_id: str):
    result = await task_scheduler.remove_task(task_id)
    if result:
        return {"success": True, "message": f"任务 {task_id} 已删除"}
    raise HTTPException(
        status_code=404,
        detail=f"任务 {task_id} 不存在"
    )


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务（保持兼容旧路由）"""
    result = await task_scheduler.remove_task(task_id)
    if result:
        return {"success": True}
    raise HTTPException(
        status_code=404,
        detail=f"任务 {task_id} 不存在"
    )


@app.post("/api/test/android")
async def test_android(device_id: str):
    """【代码质量19】测试Android设备（仅在调试模式下可用）"""
    # 通过环境变量控制是否暴露测试接口
    if os.getenv("DEBUG_MODE") != "true":
        raise HTTPException(status_code=404, detail="接口不存在")
    
    driver = await device_manager.get_device(device_id)
    if not driver:
        return {"success": False, "message": "设备未连接"}
    
    # 测试启动APP
    success = await driver.start_app()
    device_info = await driver.get_device_info()
    return {
        "success": success,
        "device_info": device_info,
    }


# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"WebSocket 客户端已连接，当前连接数: {len(active_connections)}")
    try:
        while True:
            await websocket.receive_text()   # 保持连接，忽略客户端发来的消息
    except WebSocketDisconnect:
        logger.info("WebSocket 客户端主动断开")
    except Exception as e:
        logger.warning(f"WebSocket 连接异常断开: {e}")
    finally:
        active_connections.discard(websocket)
        logger.info(f"WebSocket 连接已移除，当前连接数: {len(active_connections)}")


# ==================== 启动服务 ====================

if __name__ == "__main__":
    logger.info("启动DamaiHelper后端服务...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )


