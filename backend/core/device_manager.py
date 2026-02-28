"""
设备管理器
统一管理Android和iOS设备
"""
import asyncio
from typing import List, Dict, Optional, Union
from loguru import logger
from .android_driver import AndroidDriver
from .ios_driver import IOSDriver


class DeviceManager:
    def __init__(self):
        self.android_devices: Dict[str, AndroidDriver] = {}
        self.ios_devices: Dict[str, IOSDriver] = {}
        # 【代码质量18】使用 asyncio.Lock 替代 threading.Lock，避免阻塞事件循环
        self._lock = asyncio.Lock()
    
    async def scan_android_devices(self) -> List[str]:
        """扫描连接的Android设备"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "adb", "devices",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()
            
            devices = []
            lines = output.strip().split('\n')[1:]  # 跳过第一行标题
            for line in lines:
                # 【Critical-2修复】精确匹配 'device' 状态，避免误匹配 unauthorized/offline
                parts = line.split('\t')
                if len(parts) >= 2 and parts[1].strip() == 'device':
                    device_id = parts[0].strip()
                    devices.append(device_id)
            
            logger.info(f"扫描到 {len(devices)} 个Android设备: {devices}")
            return devices
        except FileNotFoundError:
            logger.error("ADB未安装，请先安装Android SDK")
            return []
        except Exception as e:
            logger.error(f"扫描Android设备失败: {e}")
            return []
    
    async def scan_ios_devices(self) -> List[str]:
        """扫描连接的iOS设备"""
        try:
            # 使用idevice_id命令（需要安装libimobiledevice）
            proc = await asyncio.create_subprocess_exec(
                "idevice_id", "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()
            
            devices = output.strip().split('\n')
            devices = [d for d in devices if d]  # 过滤空行
            
            logger.info(f"扫描到 {len(devices)} 个iOS设备: {devices}")
            return devices
        except FileNotFoundError:
            logger.warning("idevice_id未安装，无法扫描iOS设备")
            return []
        except Exception as e:
            logger.error(f"扫描iOS设备失败: {e}")
            return []
    
    async def connect_android_device(self, device_id: str) -> bool:
        """连接Android设备"""
        try:
            # 【BUG-D2修复】在锁内添加占位符，防止并发重入
            async with self._lock:
                if device_id in self.android_devices:
                    if self.android_devices[device_id] is not None:
                        logger.warning(f"Android设备 {device_id} 已连接，跳过重复连接")
                        return True
                    # 如果是 None（连接中），等待
                    logger.info(f"Android设备 {device_id} 正在连接中，跳过")
                    return False
                # 占位，阻止并发
                self.android_devices[device_id] = None
            
            driver = AndroidDriver(device_id)
            if await driver.connect():
                async with self._lock:
                    self.android_devices[device_id] = driver
                logger.info(f"Android设备已连接: {device_id}")
                return True
            else:
                # 连接失败，移除占位
                async with self._lock:
                    self.android_devices.pop(device_id, None)
                return False
        except Exception as e:
            logger.error(f"连接Android设备失败: {e}")
            # 异常时也要移除占位
            async with self._lock:
                self.android_devices.pop(device_id, None)
            return False
    
    async def connect_ios_device(self, device_id: str, wda_port: int = 8100, bundle_id: Optional[str] = None) -> bool:
        """连接iOS设备"""
        try:
            # 【BUG-D2修复】在锁内添加占位符，防止并发重入
            async with self._lock:
                if device_id in self.ios_devices:
                    if self.ios_devices[device_id] is not None:
                        logger.warning(f"iOS设备 {device_id} 已连接，跳过重复连接")
                        return True
                    # 如果是 None（连接中），等待
                    logger.info(f"iOS设备 {device_id} 正在连接中，跳过")
                    return False
                # 占位，阻止并发
                self.ios_devices[device_id] = None
            
            # 【BUG-D1修复】使用关键字参数传递，避免位置参数错误
            # 【High-4修复】传递 bundle_id 参数
            driver = IOSDriver(udid=device_id, wda_port=wda_port, bundle_id=bundle_id)
            if await driver.connect():
                async with self._lock:
                    self.ios_devices[device_id] = driver
                logger.info(f"iOS设备已连接: {device_id}")
                return True
            else:
                # 连接失败，移除占位
                async with self._lock:
                    self.ios_devices.pop(device_id, None)
                return False
        except Exception as e:
            logger.error(f"连接iOS设备失败: {e}")
            # 异常时也要移除占位
            async with self._lock:
                self.ios_devices.pop(device_id, None)
            return False
    
    async def get_all_devices(self) -> List[Dict]:
        """获取所有已连接设备的信息"""
        devices = []
        
        # Android设备
        async with self._lock:
            android_items = list(self.android_devices.items())
        
        for device_id, driver in android_items:
            # 【Critical-3修复】显式过滤 None driver（连接中占位状态）
            if driver is None:
                continue
            # 【BUG修复10】添加异常处理，防止单个设备异常导致整个接口失败
            try:
                info = await driver.get_device_info()
                info['platform'] = 'android'
                info['connected'] = True
                devices.append(info)
            except Exception as e:
                logger.warning(f"获取Android设备 {device_id} 信息失败: {e}")
                continue
        
        # iOS设备
        async with self._lock:
            ios_items = list(self.ios_devices.items())
        
        for device_id, driver in ios_items:
            # 【Critical-3修复】显式过滤 None driver（连接中占位状态）
            if driver is None:
                continue
            # 【BUG修复10】添加异常处理，防止单个设备异常导致整个接口失败
            try:
                info = await driver.get_device_info()
                info['platform'] = 'ios'
                info['connected'] = True
                devices.append(info)
            except Exception as e:
                logger.warning(f"获取iOS设备 {device_id} 信息失败: {e}")
                continue
        
        return devices
    
    async def get_device(self, device_id: str) -> Optional[Union[AndroidDriver, IOSDriver]]:
        """获取指定设备的驱动"""
        async with self._lock:
            if device_id in self.android_devices:
                return self.android_devices[device_id]
            elif device_id in self.ios_devices:
                return self.ios_devices[device_id]
        return None
    
    async def get_device_by_platform(self, device_id: str, platform: str) -> Optional[Union[AndroidDriver, IOSDriver]]:
        """【BUG修复11】根据平台获取指定设备的驱动，供 scheduler 使用"""
        async with self._lock:
            if platform == "android":
                return self.android_devices.get(device_id)
            else:
                return self.ios_devices.get(device_id)
        # 【BUG修复9】删除死代码：async with 块内所有分支都有 return
    
    async def disconnect_device(self, device_id: str):
        """断开设备连接"""
        async with self._lock:
            if device_id in self.android_devices:
                driver = self.android_devices[device_id]
                del self.android_devices[device_id]
                device_type = "Android"
            elif device_id in self.ios_devices:
                driver = self.ios_devices[device_id]
                del self.ios_devices[device_id]
                device_type = "iOS"
            else:
                return False  # 【BUG修复1】设备不存在时返回 False
        
        # 【Critical-1修复】判断 driver 是否为 None（连接中占位状态），避免 AttributeError
        if driver is None:
            logger.warning(f"设备 {device_id} 处于连接中状态，无需断开")
            return False
        
        # 在锁外执行耗时的断开操作
        await driver.disconnect()
        logger.info(f"{device_type}设备已断开: {device_id}")
        return True  # 【BUG修复1】设备成功断开后返回 True
    
    async def disconnect_all(self):
        """断开所有设备"""
        async with self._lock:
            android_ids = list(self.android_devices.keys())
            ios_ids = list(self.ios_devices.keys())
        
        for device_id in android_ids:
            await self.disconnect_device(device_id)
        for device_id in ios_ids:
            await self.disconnect_device(device_id)
        logger.info("所有设备已断开")


if __name__ == "__main__":
    # 测试代码
    async def test_device_manager():
        manager = DeviceManager()
        
        print("扫描Android设备...")
        android_devices = await manager.scan_android_devices()
        for device_id in android_devices:
            await manager.connect_android_device(device_id)
        
        print("扫描iOS设备...")
        ios_devices = await manager.scan_ios_devices()
        for device_id in ios_devices:
            await manager.connect_ios_device(device_id)
        
        print("\n所有已连接设备:")
        for device in await manager.get_all_devices():
            print(device)
        
        # 清理
        await manager.disconnect_all()
    
    asyncio.run(test_device_manager())

