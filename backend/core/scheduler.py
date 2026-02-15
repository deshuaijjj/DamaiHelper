"""
任务调度器
管理抢票任务的执行
"""
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from pydantic import BaseModel


class TicketTask(BaseModel):
    """抢票任务模型"""
    task_id: str
    event_name: str
    event_url: str
    start_time: str  # ISO格式时间字符串
    target_price: Optional[int] = None
    quantity: int = 1
    device_ids: List[str] = []
    status: str = "pending"  # pending, running, success, failed
    

class TaskScheduler:
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.tasks: Dict[str, TicketTask] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        
    def add_task(self, task: TicketTask) -> bool:
        """添加任务"""
        try:
            self.tasks[task.task_id] = task
            logger.info(f"任务已添加: {task.task_id} - {task.event_name}")
            return True
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            return False
    
    def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            # 如果任务正在运行，先停止
            if task_id in self.running_tasks:
                self.stop_task(task_id)
            del self.tasks[task_id]
            logger.info(f"任务已删除: {task_id}")
            return True
        return False
    
    def start_task(self, task_id: str) -> bool:
        """启动任务"""
        if task_id not in self.tasks:
            logger.error(f"任务不存在: {task_id}")
            return False
        
        task = self.tasks[task_id]
        
        # 创建任务线程
        thread = threading.Thread(target=self._run_task, args=(task,))
        self.running_tasks[task_id] = thread
        thread.start()
        
        logger.info(f"任务已启动: {task_id}")
        return True
    
    def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        if task_id in self.running_tasks:
            # 注意：这里简化处理，实际需要更优雅的停止机制
            self.tasks[task_id].status = "stopped"
            logger.info(f"任务已停止: {task_id}")
            return True
        return False
    
    def _run_task(self, task: TicketTask):
        """执行任务的内部方法"""
        try:
            task.status = "running"
            logger.info(f"开始执行任务: {task.task_id}")
            
            # 解析开票时间
            start_time = datetime.fromisoformat(task.start_time)
            
            # 等待到开票前30秒
            now = datetime.now()
            wait_seconds = (start_time - now).total_seconds() - 30
            
            if wait_seconds > 0:
                logger.info(f"等待开票，剩余时间: {wait_seconds}秒")
                time.sleep(wait_seconds)
            
            # 提前30秒准备
            logger.info("开始准备抢票...")
            self._prepare_devices(task)
            
            # 等待到开票时间
            now = datetime.now()
            wait_seconds = (start_time - now).total_seconds()
            if wait_seconds > 0:
                logger.info(f"准备完成，等待开票: {wait_seconds}秒")
                time.sleep(wait_seconds)
            
            # 开始抢票
            logger.info("开票时间到！开始抢票...")
            success = self._rush_ticket(task)
            
            if success:
                task.status = "success"
                logger.info(f"抢票成功: {task.task_id}")
            else:
                task.status = "failed"
                logger.error(f"抢票失败: {task.task_id}")
                
        except Exception as e:
            task.status = "failed"
            logger.error(f"任务执行失败: {e}")
    
    def _prepare_devices(self, task: TicketTask):
        """准备设备"""
        for device_id in task.device_ids:
            driver = self.device_manager.get_device(device_id)
            if driver:
                # 启动APP
                driver.start_app()
                logger.info(f"设备 {device_id} 已准备就绪")
    
    def _rush_ticket(self, task: TicketTask) -> bool:
        """执行抢票"""
        threads = []
        results = []
        
        # 多设备并发抢票
        for device_id in task.device_ids:
            driver = self.device_manager.get_device(device_id)
            if driver:
                thread = threading.Thread(
                    target=self._rush_on_device,
                    args=(driver, task, results)
                )
                threads.append(thread)
                thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 只要有一个成功就算成功
        return any(results)
    
    def _rush_on_device(self, driver, task: TicketTask, results: list):
        """在单个设备上抢票"""
        try:
            success = driver.rush_ticket(task.event_url)
            results.append(success)
        except Exception as e:
            logger.error(f"设备抢票失败: {e}")
            results.append(False)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            return {
                "task_id": task.task_id,
                "event_name": task.event_name,
                "status": task.status,
                "start_time": task.start_time
            }
        return None
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        return [
            {
                "task_id": task.task_id,
                "event_name": task.event_name,
                "status": task.status,
                "start_time": task.start_time
            }
            for task in self.tasks.values()
        ]

