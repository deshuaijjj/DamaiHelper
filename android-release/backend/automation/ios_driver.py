"""
iOS自动化驱动
使用WebDriverAgent控制iOS设备
"""
import wda
import time
from typing import Optional, Tuple
from loguru import logger


class IOSDriver:
    def __init__(self, device_id: Optional[str] = None, wda_port: int = 8100):
        """
        初始化iOS驱动
        :param device_id: 设备UDID
        :param wda_port: WebDriverAgent端口
        """
        self.device_id = device_id
        self.wda_port = wda_port
        self.client = None
        self.session = None
        self.bundle_id = "com.taobao.damai"  # 大麦APP Bundle ID
        
    def connect(self) -> bool:
        """连接设备"""
        try:
            # 连接到WebDriverAgent
            wda_url = f"http://localhost:{self.wda_port}"
            self.client = wda.Client(wda_url)
            
            # 获取设备信息
            status = self.client.status()
            logger.info(f"成功连接到iOS设备: {status}")
            return True
        except Exception as e:
            logger.error(f"连接iOS设备失败: {e}")
            return False
    
    def get_device_info(self) -> dict:
        """获取设备信息"""
        if not self.client:
            return {}
        
        try:
            status = self.client.status()
            return {
                "device_id": self.device_id,
                "model": status.get("ios", {}).get("model", "Unknown"),
                "version": status.get("ios", {}).get("version", "Unknown"),
                "name": status.get("ios", {}).get("name", "Unknown")
            }
        except:
            return {}
    
    def is_app_installed(self) -> bool:
        """检查大麦APP是否已安装"""
        try:
            app_state = self.client.app_state(self.bundle_id)
            return app_state is not None
        except:
            return False
    
    def start_app(self) -> bool:
        """启动大麦APP"""
        try:
            self.session = self.client.session(self.bundle_id)
            logger.info("大麦APP已启动")
            time.sleep(2)  # 等待APP启动
            return True
        except Exception as e:
            logger.error(f"启动APP失败: {e}")
            return False
    
    def stop_app(self) -> bool:
        """停止大麦APP"""
        try:
            self.client.app_terminate(self.bundle_id)
            logger.info("大麦APP已停止")
            return True
        except Exception as e:
            logger.error(f"停止APP失败: {e}")
            return False
    
    def click(self, x: int, y: int) -> bool:
        """点击指定坐标"""
        try:
            self.session.tap(x, y)
            logger.info(f"点击坐标: ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"点击失败: {e}")
            return False
    
    def click_element(self, text: str = None, label: str = None) -> bool:
        """
        点击元素
        :param text: 元素文本
        :param label: 元素标签
        """
        try:
            if text:
                element = self.session(name=text)
            elif label:
                element = self.session(label=label)
            else:
                return False
            
            if element.exists:
                element.click()
                logger.info(f"点击元素成功: text={text}, label={label}")
                return True
            else:
                logger.warning(f"元素不存在: text={text}, label={label}")
                return False
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            return False
    
    def swipe(self, fx: int, fy: int, tx: int, ty: int, duration: float = 0.5) -> bool:
        """滑动"""
        try:
            self.session.swipe(fx, fy, tx, ty, duration)
            logger.info(f"滑动: ({fx},{fy}) -> ({tx},{ty})")
            return True
        except Exception as e:
            logger.error(f"滑动失败: {e}")
            return False
    
    def screenshot(self, save_path: str = None):
        """截图"""
        try:
            if save_path:
                self.session.screenshot(save_path)
                logger.info(f"截图已保存: {save_path}")
                return save_path
            else:
                return self.session.screenshot()
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None
    
    def wait_element(self, text: str = None, label: str = None, timeout: int = 10) -> bool:
        """等待元素出现"""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if text:
                    element = self.session(name=text)
                elif label:
                    element = self.session(label=label)
                else:
                    return False
                
                if element.exists:
                    return True
                time.sleep(0.5)
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
            element = self.session(name=text)
            if element.exists:
                bounds = element.bounds
                center_x = bounds.x + bounds.width // 2
                center_y = bounds.y + bounds.height // 2
                logger.info(f"找到购买按钮(文本): {text} at ({center_x}, {center_y})")
                return (center_x, center_y)
        
        # 策略2: 通过label查找
        for text in buy_texts:
            element = self.session(label=text)
            if element.exists:
                bounds = element.bounds
                center_x = bounds.x + bounds.width // 2
                center_y = bounds.y + bounds.height // 2
                logger.info(f"找到购买按钮(label): {text} at ({center_x}, {center_y})")
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
        if self.session:
            self.session.close()
        self.client = None
        logger.info("设备已断开")


if __name__ == "__main__":
    # 测试代码
    driver = IOSDriver()
    if driver.connect():
        print("设备信息:", driver.get_device_info())
        print("大麦APP已安装:", driver.is_app_installed())

