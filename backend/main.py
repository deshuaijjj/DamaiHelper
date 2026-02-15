"""
FastAPI后端服务
提供REST API和WebSocket接口
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import asyncio
from loguru import logger

from core.device_manager import DeviceManager
from core.scheduler import TaskScheduler, TicketTask

# 初始化FastAPI
app = FastAPI(title="DamaiHelper API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化管理器
device_manager = DeviceManager()
task_scheduler = TaskScheduler(device_manager)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()


# ==================== API路由 ====================

@app.get("/")
async def root():
    return {"message": "DamaiHelper API is running"}


@app.get("/api/devices/scan")
async def scan_devices():
    """扫描所有设备"""
    android_devices = device_manager.scan_android_devices()
    ios_devices = device_manager.scan_ios_devices()
    
    return {
        "android": android_devices,
        "ios": ios_devices
    }


@app.post("/api/devices/connect")
async def connect_device(device_id: str, platform: str):
    """连接设备"""
    if platform == "android":
        success = device_manager.connect_android_device(device_id)
    elif platform == "ios":
        success = device_manager.connect_ios_device(device_id)
    else:
        return {"success": False, "message": "不支持的平台"}
    
    if success:
        # 广播设备连接事件
        await manager.broadcast({
            "type": "device_connected",
            "device_id": device_id,
            "platform": platform
        })
    
    return {"success": success}


@app.get("/api/devices")
async def get_devices():
    """获取所有已连接设备"""
    devices = device_manager.get_all_devices()
    return {"devices": devices}


@app.post("/api/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str):
    """断开设备"""
    device_manager.disconnect_device(device_id)
    
    await manager.broadcast({
        "type": "device_disconnected",
        "device_id": device_id
    })
    
    return {"success": True}


@app.post("/api/tasks")
async def create_task(task: TicketTask):
    """创建抢票任务"""
    success = task_scheduler.add_task(task)
    return {"success": success, "task_id": task.task_id}


@app.get("/api/tasks")
async def get_tasks():
    """获取所有任务"""
    tasks = task_scheduler.get_all_tasks()
    return {"tasks": tasks}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    task = task_scheduler.get_task_status(task_id)
    if task:
        return task
    return {"error": "任务不存在"}


@app.post("/api/tasks/{task_id}/start")
async def start_task(task_id: str):
    """启动任务"""
    success = task_scheduler.start_task(task_id)
    
    if success:
        await manager.broadcast({
            "type": "task_started",
            "task_id": task_id
        })
    
    return {"success": success}


@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    """停止任务"""
    success = task_scheduler.stop_task(task_id)
    
    if success:
        await manager.broadcast({
            "type": "task_stopped",
            "task_id": task_id
        })
    
    return {"success": success}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    success = task_scheduler.remove_task(task_id)
    return {"success": success}


@app.post("/api/test/android")
async def test_android(device_id: str):
    """测试Android设备"""
    driver = device_manager.get_device(device_id)
    if not driver:
        return {"success": False, "message": "设备未连接"}
    
    # 测试启动APP
    success = driver.start_app()
    return {
        "success": success,
        "device_info": driver.get_device_info(),
        "app_installed": driver.is_app_installed()
    }


# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接，用于实时推送"""
    await manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            
            # 处理不同类型的消息
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket连接已断开")


# ==================== 启动服务 ====================

if __name__ == "__main__":
    logger.info("启动DamaiHelper后端服务...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

