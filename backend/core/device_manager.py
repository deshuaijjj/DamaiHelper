"""
设备管理器
统一管理Android和iOS设备
"""
from typing import List, Dict, Optional
from loguru import logger
import subprocess
from .android_driver import AndroidDriver
from .ios_driver import IOSDriver


class DeviceManager:
    def __init__(self):
        self.android_devices: Dict[str, AndroidDriver] = {}
        self.ios_devices: Dict[str, IOSDriver] = {}
    
    def scan_android_devices(self) -> List[str]:
        """扫描连接的Android设备"""
        try:
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            devices = []
            lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行标题
            for line in lines:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
            
            logger.info(f"扫描到 {len(devices)} 个Android设备: {devices}")
            return devices
        except FileNotFoundError:
            logger.error("ADB未安装，请先安装Android SDK")
            return []
        except Exception as e:
            logger.error(f"扫描Android设备失败: {e}")
            return []
    
    def scan_ios_devices(self) -> List[str]:
        """扫描连接的iOS设备"""
        try:
            # 使用idevice_id命令（需要安装libimobiledevice）
            result = subprocess.run(
                ['idevice_id', '-l'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            devices = result.stdout.strip().split('\n')
            devices = [d for d in devices if d]  # 过滤空行
            
            logger.info(f"扫描到 {len(devices)} 个iOS设备: {devices}")
            return devices
        except FileNotFoundError:
            logger.warning("idevice_id未安装，无法扫描iOS设备")
            return []
        except Exception as e:
            logger.error(f"扫描iOS设备失败: {e}")
            return []
    
    def connect_android_device(self, device_id: str) -> bool:
        """连接Android设备"""
        try:
            driver = AndroidDriver(device_id)
            if driver.connect():
                self.android_devices[device_id] = driver
                logger.info(f"Android设备已连接: {device_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"连接Android设备失败: {e}")
            return False
    
    def connect_ios_device(self, device_id: str, wda_port: int = 8100) -> bool:
        """连接iOS设备"""
        try:
            driver = IOSDriver(device_id, wda_port)
            if driver.connect():
                self.ios_devices[device_id] = driver
                logger.info(f"iOS设备已连接: {device_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"连接iOS设备失败: {e}")
            return False
    
    def get_all_devices(self) -> List[Dict]:
        """获取所有已连接设备的信息"""
        devices = []
        
        # Android设备
        for device_id, driver in self.android_devices.items():
            info = driver.get_device_info()
            info['platform'] = 'android'
            info['connected'] = True
            devices.append(info)
        
        # iOS设备
        for device_id, driver in self.ios_devices.items():
            info = driver.get_device_info()
            info['platform'] = 'ios'
            info['connected'] = True
            devices.append(info)
        
        return devices
    
    def get_device(self, device_id: str) -> Optional[AndroidDriver | IOSDriver]:
        """获取指定设备的驱动"""
        if device_id in self.android_devices:
            return self.android_devices[device_id]
        elif device_id in self.ios_devices:
            return self.ios_devices[device_id]
        return None
    
    def disconnect_device(self, device_id: str):
        """断开设备连接"""
        if device_id in self.android_devices:
            self.android_devices[device_id].disconnect()
            del self.android_devices[device_id]
            logger.info(f"Android设备已断开: {device_id}")
        elif device_id in self.ios_devices:
            self.ios_devices[device_id].disconnect()
            del self.ios_devices[device_id]
            logger.info(f"iOS设备已断开: {device_id}")
    
    def disconnect_all(self):
        """断开所有设备"""
        for device_id in list(self.android_devices.keys()):
            self.disconnect_device(device_id)
        for device_id in list(self.ios_devices.keys()):
            self.disconnect_device(device_id)
        logger.info("所有设备已断开")


if __name__ == "__main__":
    # 测试代码
    manager = DeviceManager()
    
    print("扫描Android设备...")
    android_devices = manager.scan_android_devices()
    for device_id in android_devices:
        manager.connect_android_device(device_id)
    
    print("扫描iOS设备...")
    ios_devices = manager.scan_ios_devices()
    for device_id in ios_devices:
        manager.connect_ios_device(device_id)
    
    print("\n所有已连接设备:")
    for device in manager.get_all_devices():
        print(device)

