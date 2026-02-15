"""
Android自动化驱动
使用uiautomator2控制Android设备
"""
import uiautomator2 as u2
import time
from typing import Optional, Tuple
from loguru import logger


class AndroidDriver:
    def __init__(self, device_id: Optional[str] = None):
        """
        初始化Android驱动
        :param device_id: 设备ID，如果为None则连接第一个设备
        """
        self.device_id = device_id
        self.device = None
        self.app_package = "cn.damai"  # 大麦APP包名
        
    def connect(self) -> bool:
        """连接设备"""
        try:
            if self.device_id:
                self.device = u2.connect(self.device_id)
            else:
                self.device = u2.connect()
            
            logger.info(f"成功连接到设备: {self.device.info}")
            return True
        except Exception as e:
            logger.error(f"连接设备失败: {e}")
            return False
    
    def get_device_info(self) -> dict:
        """获取设备信息"""
        if not self.device:
            return {}
        
        info = self.device.info
        return {
            "device_id": self.device_id,
            "brand": info.get("brand", "Unknown"),
            "model": info.get("model", "Unknown"),
            "version": info.get("version", "Unknown"),
            "display": f"{info.get('displayWidth', 0)}x{info.get('displayHeight', 0)}"
        }
    
    def is_app_installed(self) -> bool:
        """检查大麦APP是否已安装"""
        try:
            return self.device.app_info(self.app_package) is not None
        except:
            return False
    
    def start_app(self) -> bool:
        """启动大麦APP"""
        try:
            self.device.app_start(self.app_package)
            logger.info("大麦APP已启动")
            time.sleep(2)  # 等待APP启动
            return True
        except Exception as e:
            logger.error(f"启动APP失败: {e}")
            return False
    
    def stop_app(self) -> bool:
        """停止大麦APP"""
        try:
            self.device.app_stop(self.app_package)
            logger.info("大麦APP已停止")
            return True
        except Exception as e:
            logger.error(f"停止APP失败: {e}")
            return False
    
    def click(self, x: int, y: int) -> bool:
        """点击指定坐标"""
        try:
            self.device.click(x, y)
            logger.info(f"点击坐标: ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"点击失败: {e}")
            return False
    
    def click_element(self, text: str = None, resource_id: str = None) -> bool:
        """
        点击元素
        :param text: 元素文本
        :param resource_id: 元素资源ID
        """
        try:
            if text:
                element = self.device(text=text)
            elif resource_id:
                element = self.device(resourceId=resource_id)
            else:
                return False
            
            if element.exists:
                element.click()
                logger.info(f"点击元素成功: text={text}, id={resource_id}")
                return True
            else:
                logger.warning(f"元素不存在: text={text}, id={resource_id}")
                return False
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            return False
    
    def swipe(self, fx: int, fy: int, tx: int, ty: int, duration: float = 0.5) -> bool:
        """滑动"""
        try:
            self.device.swipe(fx, fy, tx, ty, duration)
            logger.info(f"滑动: ({fx},{fy}) -> ({tx},{ty})")
            return True
        except Exception as e:
            logger.error(f"滑动失败: {e}")
            return False
    
    def get_text(self, text: str = None, resource_id: str = None) -> Optional[str]:
        """获取元素文本"""
        try:
            if text:
                element = self.device(text=text)
            elif resource_id:
                element = self.device(resourceId=resource_id)
            else:
                return None
            
            if element.exists:
                return element.get_text()
            return None
        except Exception as e:
            logger.error(f"获取文本失败: {e}")
            return None
    
    def screenshot(self, save_path: str = None) -> Optional[str]:
        """截图"""
        try:
            if save_path:
                self.device.screenshot(save_path)
                logger.info(f"截图已保存: {save_path}")
                return save_path
            else:
                # 返回PIL Image对象
                return self.device.screenshot()
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None
    
    def wait_element(self, text: str = None, resource_id: str = None, timeout: int = 10) -> bool:
        """等待元素出现"""
        try:
            if text:
                return self.device(text=text).wait(timeout=timeout)
            elif resource_id:
                return self.device(resourceId=resource_id).wait(timeout=timeout)
            return False
        except Exception as e:
            logger.error(f"等待元素失败: {e}")
            return False
    
    def find_buy_button(self) -> Optional[Tuple[int, int]]:
        """
        查找购买按钮
        使用多种策略定位
        """
        # 策略1: 通过文本查找
        buy_texts = ["立即购买", "立即预订", "马上抢", "立即抢购"]
        for text in buy_texts:
            element = self.device(text=text)
            if element.exists:
                info = element.info
                center_x = info['bounds']['left'] + (info['bounds']['right'] - info['bounds']['left']) // 2
                center_y = info['bounds']['top'] + (info['bounds']['bottom'] - info['bounds']['top']) // 2
                logger.info(f"找到购买按钮(文本): {text} at ({center_x}, {center_y})")
                return (center_x, center_y)
        
        # 策略2: 通过资源ID查找
        resource_ids = [
            "cn.damai:id/buy_button",
            "cn.damai:id/btn_buy",
            "cn.damai:id/purchase_btn"
        ]
        for res_id in resource_ids:
            element = self.device(resourceId=res_id)
            if element.exists:
                info = element.info
                center_x = info['bounds']['left'] + (info['bounds']['right'] - info['bounds']['left']) // 2
                center_y = info['bounds']['top'] + (info['bounds']['bottom'] - info['bounds']['top']) // 2
                logger.info(f"找到购买按钮(ID): {res_id} at ({center_x}, {center_y})")
                return (center_x, center_y)
        
        logger.warning("未找到购买按钮")
        return None
    
    def rush_ticket(self, event_url: str) -> bool:
        """
        抢票主流程
        :param event_url: 演出详情页URL
        """
        try:
            logger.info("开始抢票流程")
            
            # 1. 启动APP
            if not self.start_app():
                return False
            
            time.sleep(2)
            
            # 2. 查找购买按钮
            buy_button = self.find_buy_button()
            if not buy_button:
                logger.error("未找到购买按钮")
                return False
            
            # 3. 点击购买按钮
            self.click(buy_button[0], buy_button[1])
            time.sleep(1)
            
            # 4. 等待选座页面
            logger.info("等待选座页面...")
            time.sleep(2)
            
            # 5. 查找确认按钮
            confirm_texts = ["确认", "提交订单", "确定"]
            for text in confirm_texts:
                if self.click_element(text=text):
                    logger.info("点击确认按钮成功")
                    return True
            
            logger.warning("未找到确认按钮")
            return False
            
        except Exception as e:
            logger.error(f"抢票流程失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.device = None
        logger.info("设备已断开")


if __name__ == "__main__":
    # 测试代码
    driver = AndroidDriver()
    if driver.connect():
        print("设备信息:", driver.get_device_info())
        print("大麦APP已安装:", driver.is_app_installed())

