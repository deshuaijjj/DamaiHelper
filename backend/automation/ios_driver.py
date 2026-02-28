"""
ios_driver.py
iOS 设备驱动 —— 基于 Appium + XCUITest 控制大麦 APP 完成抢票流程

依赖：
    pip install Appium-Python-Client selenium
系统依赖（Mac）：
    brew install libimobiledevice   # 提供 ideviceinfo 命令
    Xcode + WebDriverAgent          # Appium 自动管理
"""

import asyncio
import logging
import re
import subprocess
import threading
import time
from typing import Optional, Union

from appium import webdriver
from appium.options import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

# ── 大麦 iOS APP 基本信息 ──────────────────────────────────────
DAMAI_BUNDLE_ID = "cn.damai"                        # App Store Bundle ID
DAMAI_URL_SCHEME = "damai://"                       # URL Scheme 前缀

# ── 默认超时（秒） ─────────────────────────────────────────────
SHORT_WAIT  = 3
NORMAL_WAIT = 10
LONG_WAIT   = 30

# ── iOS 元素定位策略（比 XPath 快 3~5 倍） ────────────────────
# Predicate String 语法参考：
#   https://github.com/facebookarchive/WebDriverAgent/wiki/Predicate-Queries-Construction-Rules
# Class Chain 语法参考：
#   https://github.com/facebookarchive/WebDriverAgent/wiki/Class-Chain-Queries-Construction-Rules

# 购买按钮
_PRED_BUY_BTN = (
    'type == "XCUIElementTypeButton" AND '
    '(label CONTAINS "立即购买" OR label CONTAINS "购买") AND '
    'enabled == true'
)
# 票档列表容器
_CC_TICKET_LIST = "**/XCUIElementTypeScrollView/XCUIElementTypeOther"
# 票档单项
_PRED_TICKET_ITEM = 'type == "XCUIElementTypeCell" OR type == "XCUIElementTypeOther"'
# 售罄标记
_PRED_SOLD_OUT = (
    '(label CONTAINS "售罄" OR label CONTAINS "暂无" OR '
    'label CONTAINS "缺货" OR label CONTAINS "已售完")'
)
# 数量加减
_PRED_QTY_LABEL = 'type == "XCUIElementTypeStaticText" AND value MATCHES "^[0-9]+$"'
_PRED_QTY_PLUS  = 'label == "+" OR label CONTAINS "加" OR name CONTAINS "add"'
# 确认 / 下一步
_PRED_CONFIRM = (
    'type == "XCUIElementTypeButton" AND '
    '(label == "确定" OR label == "下一步" OR label CONTAINS "确认") AND '
    'enabled == true'
)
# 购票人列表
_CC_BUYER_LIST = "**/XCUIElementTypeTableView/XCUIElementTypeCell"
# 提交订单
_PRED_SUBMIT = (
    'type == "XCUIElementTypeButton" AND '
    '(label CONTAINS "提交订单" OR label CONTAINS "立即支付") AND '
    'enabled == true'
)
# 弹窗关闭
_PRED_POPUP_CLOSE = (
    'type == "XCUIElementTypeButton" AND '
    '(label == "关闭" OR label == "取消" OR label CONTAINS "我知道了" '
    'OR label == "×" OR name == "close")'
)


class IOSDriver:
    """
    封装单台 iOS 设备的所有操作。
    每台设备对应一个实例，由 DeviceManager 统一管理。

    与 AndroidDriver 保持相同的公开接口：
        connect / disconnect / get_device_info /
        start_app / navigate_to_event / rush_ticket
    """

    def __init__(
        self,
        udid:          str,
        appium_server: str = "http://127.0.0.1:4723",
        wda_port:      int = 8100,
        bundle_id:     Optional[str] = None,  # 【关键问题1修复】添加 bundle_id 参数
    ):
        """
        :param udid:          iOS 设备 UDID（40位十六进制字符串）
        :param appium_server: Appium Server 地址
        :param wda_port:      WebDriverAgent 监听端口（多设备时需各不相同）
        :param bundle_id:     APP Bundle ID，默认使用大麦 APP
        """
        self.udid          = udid
        self.appium_server = appium_server
        self.wda_port      = wda_port
        self.bundle_id     = bundle_id or DAMAI_BUNDLE_ID  # 【关键问题1修复】存储 bundle_id
        self.driver: Optional[webdriver.Remote] = None
        self._connected    = False

    # ══════════════════════════════════════════════════════════════
    # 连接 / 断开
    # ══════════════════════════════════════════════════════════════

    async def connect(self) -> bool:
        """
        初始化 Appium / XCUITest 会话，连接 iOS 设备。
        首次连接会在设备上编译安装 WebDriverAgent（约需1~3分钟）。
        后续连接若 WDA 已存在则秒级完成。
        """
        try:
            loop = asyncio.get_running_loop()
            
            def _connect():
                options = AppiumOptions()
                options.platform_name = "iOS"
                options.set_capability("appium:automationName",    "XCUITest")
                options.set_capability("appium:udid",              self.udid)
                # 【关键问题3修复】使用传入的 bundle_id 而非硬编码
                options.set_capability("appium:bundleId",          self.bundle_id)
                options.set_capability("appium:noReset",           True)
                options.set_capability("appium:newCommandTimeout", 300)
                # WDA 相关（多设备并发时必须指定不同端口）
                options.set_capability("appium:wdaLocalPort",      self.wda_port)
                options.set_capability("appium:wdaLaunchTimeout",  120_000)   # ms
                options.set_capability("appium:wdaConnectionTimeout", 60_000) # ms
                options.set_capability("appium:useNewWDA",         False)     # 复用已有WDA
                options.set_capability("appium:usePrebuiltWDA",    False)
                # 性能优化
                options.set_capability("appium:waitForQuiescence", False)     # 不等页面静止
                options.set_capability("appium:shouldUseSingletonTestManager", False)
                return webdriver.Remote(self.appium_server, options=options)

            self.driver = await loop.run_in_executor(None, _connect)
            self._connected = True
            logger.info(f"[iOS] 设备连接成功: {self.udid}")
            return True

        except WebDriverException as e:
            logger.error(f"[iOS] 设备连接失败 {self.udid}: {e}")
            return False

    async def disconnect(self):
        """释放 Appium 会话资源（不会关闭 WDA 进程）。"""
        if self.driver:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.driver.quit)
                logger.info(f"[iOS] 设备已断开: {self.udid}")
            except Exception as e:
                logger.warning(f"[iOS] 断开时出现异常（已忽略）{self.udid}: {e}")
            finally:
                self.driver     = None
                self._connected = False

    # ══════════════════════════════════════════════════════════════
    # 设备信息
    # ══════════════════════════════════════════════════════════════

    async def get_device_info(self) -> dict:
        """
        通过 ideviceinfo（libimobiledevice）获取设备基本信息。
        不依赖 Appium，设备未连接 Appium 时也可调用。
        需要系统已安装 libimobiledevice：brew install libimobiledevice
        """
        info = {
            "device_id":   self.udid,
            "platform":    "ios",
            "model":       None,
            "name":        None,       # 【关键问题2修复】改为 name（与前端一致）
            "version":     None,       # 【关键问题2修复】改为 version（与前端一致）
            "battery":     -1,
            "screen_size": None,
        }
        try:
            loop = asyncio.get_running_loop()
            info["model"] = await loop.run_in_executor(
                None, lambda: self._idevice_info("ProductType")
            )
            # 【关键问题2修复】改为 version 字段
            info["version"] = await loop.run_in_executor(
                None, lambda: self._idevice_info("ProductVersion")
            )
            # 【关键问题2修复】改为 name 字段
            info["name"] = await loop.run_in_executor(
                None, lambda: self._idevice_info("DeviceName")
            )

            # 电量：需要 com.apple.mobile.battery 域
            battery_raw = await loop.run_in_executor(
                None,
                lambda: self._idevice_info(
                    "BatteryCurrentCapacity",
                    domain="com.apple.mobile.battery"
                )
            )
            if battery_raw and battery_raw.isdigit():
                info["battery"] = int(battery_raw)

            # 分辨率：通过 Appium 获取（需已连接）
            if self._connected and self.driver:
                size = await loop.run_in_executor(None, self.driver.get_window_size)
                info["screen_size"] = f"{size['width']}x{size['height']}"

        except Exception as e:
            logger.warning(f"[iOS] 获取设备信息部分失败 {self.udid}: {e}")
        return info

    def _idevice_info(self, key: str, domain: str = "") -> str:
        """
        调用 ideviceinfo 获取单个属性值。
        :param key:    属性名，如 "ProductVersion"
        :param domain: 可选域名，如 "com.apple.mobile.battery"
        """
        cmd = f"ideviceinfo -u {self.udid}"
        if domain:
            cmd += f" -q {domain}"
        cmd += f" -k {key}"
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            logger.debug(f"[iOS] ideviceinfo 失败 key={key}: {e}")
            return ""

    # ══════════════════════════════════════════════════════════════
    # APP 操作
    # ══════════════════════════════════════════════════════════════

    async def start_app(self) -> bool:
        """
        启动大麦 APP，等待主页 Tab 栏加载完成。
        若 APP 已在前台则直接返回 True。
        """
        if self.driver is None:
            logger.error("设备未连接")
            return False
        if not self._check_driver():
            return False
        try:
            loop = asyncio.get_running_loop()
            # 检查当前是否已是大麦
            current_bundle_info = await loop.run_in_executor(
                None,
                lambda: self.driver.execute_script("mobile: activeAppInfo", {})
            )
            current_bundle = current_bundle_info.get("bundleId", "")

            # 【关键问题3修复】使用实例的 bundle_id 进行比较
            if current_bundle == self.bundle_id:
                logger.info(f"[iOS] 大麦 APP 已在前台: {self.udid}")
                return True

            # 激活 APP
            await loop.run_in_executor(None, lambda: self.driver.activate_app(self.bundle_id))

            # 等待首页底部 Tab 栏出现（首页/演出/购物车/我的）
            tab_bar = await self._wait_for_element(
                AppiumBy.IOS_PREDICATE,
                'type == "XCUIElementTypeTabBar"',
                timeout=LONG_WAIT
            )
            if tab_bar:
                logger.info(f"[iOS] 大麦 APP 启动成功: {self.udid}")
                return True

            logger.error(f"[iOS] 大麦 APP 启动超时（Tab栏未出现）: {self.udid}")
            return False

        except Exception as e:
            logger.error(f"[iOS] 启动 APP 异常 {self.udid}: {e}")
            return False

    async def navigate_to_event(self, event_url: str) -> bool:
        """
        导航到演出详情页并等待页面加载完成。
        支持两种 URL 格式：
          - damai://damai/detail?itemId=XXXXX  （URL Scheme）
          - https://m.damai.cn/...             （H5 链接，通过 Safari 打开后跳转）
        """
        if self.driver is None:
            logger.error("设备未连接")
            return False
        if not self._check_driver():
            return False
        try:
            loop = asyncio.get_running_loop()
            logger.info(f"[iOS] 导航到演出页: {self.udid} → {event_url}")

            if event_url.startswith("damai://"):
                # URL Scheme 直接跳转
                await loop.run_in_executor(None, lambda: self.driver.get(event_url))
            else:
                # H5 链接：先打开 Safari，再通过 Universal Link 跳转到 APP
                await loop.run_in_executor(
                    None,
                    lambda: self.driver.execute_script("mobile: openUrl", {"url": event_url})
                )
                await asyncio.sleep(2)
                # 处理"在大麦中打开"弹窗
                await self._handle_open_in_app_prompt()

            # 等待详情页的购买按钮区域出现
            buy_area = await self._wait_for_element(
                AppiumBy.IOS_PREDICATE,
                'type == "XCUIElementTypeButton" AND '
                '(label CONTAINS "购买" OR label CONTAINS "开抢" '
                'OR label CONTAINS "缺货" OR label CONTAINS "暂无")',
                timeout=NORMAL_WAIT
            )
            if buy_area:
                logger.info(f"[iOS] 演出页加载完成: {self.udid}")
                return True

            logger.warning(f"[iOS] 演出页加载超时，未找到购买按钮: {self.udid}")
            return False

        except Exception as e:
            logger.error(f"[iOS] 导航演出页异常 {self.udid}: {e}")
            return False

    async def _handle_open_in_app_prompt(self):
        """
        处理 iOS 系统弹出的"在 App 中打开"提示。
        通常在通过 H5 链接跳转时出现。
        """
        try:
            loop = asyncio.get_running_loop()
            # iOS 系统 Alert
            alert = await loop.run_in_executor(None, lambda: self.driver.switch_to.alert)
            alert_text = await loop.run_in_executor(None, lambda: alert.text) or ""
            if "大麦" in alert_text or "打开" in alert_text:
                await loop.run_in_executor(None, alert.accept)
                logger.debug(f"[iOS] 已接受跳转 APP 提示: {self.udid}")
                await asyncio.sleep(1)
        except Exception:
            # 没有弹窗，正常继续
            pass

    # ══════════════════════════════════════════════════════════════
    # 核心抢票流程
    # ══════════════════════════════════════════════════════════════

    async def rush_ticket(
        self,
        event_url:      str,
        preferred_area: Optional[str]             = None,
        target_price:   Optional[int]             = None,
        quantity:       int                       = 1,
        buyer_name:     Optional[str]             = None,
        stop_event:     Optional[threading.Event] = None,
    ) -> bool:
        """
        完整抢票流程（与 AndroidDriver 接口完全一致）：
        1. 点击"立即购买"
        2. 选择票档
        3. 选择数量
        4. 选择购票人
        5. 提交订单
        返回 True 表示成功提交订单，False 表示失败或被停止。
        """
        if self.driver is None:
            logger.error("设备未连接")
            return False
        if not self._check_driver():
            return False

        logger.info(
            f"[iOS] 开始抢票 device={self.udid} "
            f"area={preferred_area} price≤{target_price} qty={quantity}"
        )

        try:
            # 【BUG-I2修复】导航到演出详情页，空 URL 时跳过
            loop = asyncio.get_running_loop()
            if event_url:
                if event_url.startswith("damai://"):
                    await loop.run_in_executor(None, lambda: self.driver.get(event_url))
                else:
                    await loop.run_in_executor(
                        None,
                        lambda: self.driver.execute_script("mobile: openUrl", {"url": event_url})
                    )
                await asyncio.sleep(2)

            # ── Step 1: 点击"立即购买" ──────────────────────────
            if self._is_stopped(stop_event):
                return False
            
            max_retries = 5
            retry_interval = 0.5
            
            for attempt in range(max_retries):
                if not await self._click_buy_button(stop_event):
                    if attempt < max_retries - 1:
                        logger.warning(f"[iOS] 点击购买按钮失败，重试 {attempt + 1}/{max_retries}")
                        await asyncio.sleep(retry_interval)
                        continue
                    else:
                        logger.error(f"[iOS] 点击购买按钮失败，已达最大重试次数")
                        return False
                break

            # ── Step 2: 选择票档 ────────────────────────────────
            if self._is_stopped(stop_event):
                return False
            if not await self._select_ticket_area(preferred_area, target_price, stop_event):
                logger.error(f"[iOS] 票档选择失败: {self.udid}")
                return False

            # ── Step 3: 选择数量 ────────────────────────────────
            if self._is_stopped(stop_event):
                return False
            await self._select_quantity(quantity)

            # ── Step 4: 点击"确定"进入下一步 ────────────────────
            if self._is_stopped(stop_event):
                return False
            await self._click_confirm_area()

            # ── Step 5: 选择购票人 ──────────────────────────────
            if self._is_stopped(stop_event):
                return False
            if not await self._select_buyer(buyer_name, quantity):
                logger.error(f"[iOS] 购票人选择失败: {self.udid}")
                return False

            # ── Step 6: 提交订单 ────────────────────────────────
            if self._is_stopped(stop_event):
                return False
            if not await self._submit_order():
                return False

            logger.info(f"[iOS] 🎉 抢票成功！device={self.udid}")
            return True

        except Exception as e:
            logger.error(f"[iOS] 抢票流程异常 {self.udid}: {e}")
            return False

    # ══════════════════════════════════════════════════════════════
    # 抢票子步骤（私有）
    # ══════════════════════════════════════════════════════════════

    async def _click_buy_button(self, stop_event: Optional[threading.Event]) -> bool:
        """
        等待并点击"立即购买"按钮。
        开票前按钮可能处于禁用状态，以 100ms 间隔轮询直到可点击。
        最长等待 60 秒（足够覆盖开票前的倒计时误差）。
        """
        logger.info(f"[iOS] 等待购买按钮激活: {self.udid}")
        deadline = time.time() + 60

        while time.time() < deadline:
            if self._is_stopped(stop_event):
                return False

            # 先处理可能遮挡的弹窗
            await self._dismiss_popup()

            btn = await self._find_element(AppiumBy.IOS_PREDICATE, _PRED_BUY_BTN)
            if btn:
                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, btn.click)
                    logger.info(f"[iOS] 已点击立即购买: {self.udid}")
                    await asyncio.sleep(0.5)
                    return True
                except Exception as e:
                    logger.debug(f"[iOS] 点击购买按钮失败，重试: {e}")

            await asyncio.sleep(0.1)  # 100ms 轮询

        logger.error(f"[iOS] 等待购买按钮超时（60s）: {self.udid}")
        return False

    async def _select_ticket_area(
        self,
        preferred_area: Optional[str],
        target_price:   Optional[int],
        stop_event:     Optional[threading.Event],
    ) -> bool:
        """
        在票档选择半屏弹出页选择合适的票档。
        优先级：preferred_area > target_price（≤上限的最低价） > 第一个可购买票档
        """
        # 等待票档弹出页出现（半屏 Sheet）
        sheet = await self._wait_for_element(
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeSheet" OR type == "XCUIElementTypeScrollView"',
            timeout=NORMAL_WAIT
        )
        if not sheet:
            # 可能只有单一票档，直接跳过选择
            logger.info(f"[iOS] 未出现票档选择页，可能为单一票档: {self.udid}")
            return True

        if self._is_stopped(stop_event):
            return False

        try:
            loop = asyncio.get_running_loop()
            # 获取所有票档条目
            items = await self._find_elements(
                AppiumBy.IOS_CLASS_CHAIN,
                "**/XCUIElementTypeCell"
            )
            if not items:
                # 兜底：使用 Other 类型
                items = await self._find_elements(
                    AppiumBy.IOS_PREDICATE,
                    'type == "XCUIElementTypeOther" AND visible == true'
                )

            if not items:
                logger.info(f"[iOS] 票档列表为空，尝试直接继续: {self.udid}")
                return True

            selected = None

            # ── 策略1：按名称匹配 ──────────────────────────────
            if preferred_area:
                for item in items:
                    try:
                        labels = await loop.run_in_executor(
                            None,
                            lambda i=item: i.find_elements(
                                AppiumBy.IOS_PREDICATE,
                                'type == "XCUIElementTypeStaticText"'
                            )
                        )
                        # 【性能优化5修复】使用 executor 访问 el.text
                        label_texts = []
                        for el in labels:
                            text = await loop.run_in_executor(None, lambda e=el: e.text if e.text else "")
                            label_texts.append(text)
                        item_text = " ".join(label_texts)
                        sold_out  = await self._is_element_sold_out(item)
                        if preferred_area in item_text and not sold_out:
                            selected = item
                            logger.info(f"[iOS] 按名称匹配票档: {item_text[:30]}")
                            break
                    except Exception:
                        continue

            # ── 策略2：按价格筛选 ──────────────────────────────
            if not selected and target_price is not None:
                best_price = None
                best_item  = None
                for item in items:
                    try:
                        if await self._is_element_sold_out(item):
                            continue
                        labels = await loop.run_in_executor(
                            None,
                            lambda i=item: i.find_elements(
                                AppiumBy.IOS_PREDICATE,
                                'type == "XCUIElementTypeStaticText"'
                            )
                        )
                        # 【性能优化5修复】使用 executor 访问 el.text
                        label_texts = []
                        for el in labels:
                            text = await loop.run_in_executor(None, lambda e=el: e.text if e.text else "")
                            label_texts.append(text)
                        item_text = " ".join(label_texts)
                        price = self._parse_price(item_text)
                        if price is None:
                            continue
                        # 选价格 ≤ 上限中最低的那档
                        if price <= target_price:
                            if best_price is None or price < best_price:
                                best_price = price
                                best_item  = item
                    except Exception:
                        continue

                if best_item:
                    selected = best_item
                    logger.info(
                        f"[iOS] 按价格匹配票档: ¥{best_price} "
                        f"(上限 ¥{target_price}): {self.udid}"
                    )

            # ── 策略3：选第一个可购买的票档 ──────────────────────
            if not selected:
                for item in items:
                    try:
                        if not await self._is_element_sold_out(item):
                            selected = item
                            labels = await loop.run_in_executor(
                                None,
                                lambda i=item: i.find_elements(
                                    AppiumBy.IOS_PREDICATE,
                                    'type == "XCUIElementTypeStaticText"'
                                )
                            )
                            # 【性能优化5修复】使用 executor 访问 el.text
                            label_texts = []
                            for el in labels:
                                text = await loop.run_in_executor(None, lambda e=el: e.text if e.text else "")
                                label_texts.append(text)
                            item_text = " ".join(label_texts)
                            logger.info(
                                f"[iOS] 选第一个可购买票档: "
                                f"{item_text[:30]}: {self.udid}"
                            )
                            break
                    except Exception:
                        continue

            if not selected:
                logger.error(f"[iOS] 所有票档均已售罄: {self.udid}")
                return False

            # ── 点击选中的票档 ────────────────────────────────────
            try:
                await loop.run_in_executor(None, selected.click)
                logger.info(f"[iOS] 票档已选中: {self.udid}")
                await asyncio.sleep(0.3)
                return True
            except Exception as e:
                logger.error(f"[iOS] 点击票档失败 {self.udid}: {e}")
                return False

        except Exception as e:
            logger.error(f"[iOS] 票档选择流程异常 {self.udid}: {e}")
            return False

    async def _select_quantity(self, quantity: int):
        """
        设置购票数量。
        默认数量为 1，若需要更多则连续点击"+"按钮。
        iOS 上数量控件通常是 Stepper 或自定义加减按钮。
        """
        if quantity <= 1:
            return  # 默认已是 1 张，无需操作

        logger.info(f"[iOS] 设置购票数量: {quantity}: {self.udid}")

        # 等待数量控件出现
        await asyncio.sleep(0.5)

        loop = asyncio.get_running_loop()
        for attempt in range(quantity - 1):
            # 优先找 XCUIElementTypeStepper 的增加按钮
            plus_btn = await self._find_element(
                AppiumBy.IOS_PREDICATE,
                'type == "XCUIElementTypeButton" AND '
                '(label == "+" OR label == "Increment" OR '
                'label CONTAINS "增加" OR name CONTAINS "plus" OR '
                'name CONTAINS "add" OR name CONTAINS "increase")'
            )
            if not plus_btn:
                # 兜底：找 Stepper 控件本身
                stepper = await self._find_element(
                    AppiumBy.IOS_PREDICATE,
                    'type == "XCUIElementTypeStepper"'
                )
                if stepper:
                    # Stepper 的第二个子按钮通常是"+"
                    btns = await loop.run_in_executor(
                        None,
                        lambda: stepper.find_elements(
                            AppiumBy.IOS_PREDICATE,
                            'type == "XCUIElementTypeButton"'
                        )
                    )
                    if len(btns) >= 2:
                        plus_btn = btns[1]

            if plus_btn:
                try:
                    await loop.run_in_executor(None, plus_btn.click)
                    logger.debug(
                        f"[iOS] 数量 +1 → {attempt + 2}/{quantity}: {self.udid}"
                    )
                    await asyncio.sleep(0.2)
                except Exception as e:
                    logger.warning(f"[iOS] 点击+号失败 attempt={attempt}: {e}")
            else:
                logger.warning(
                    f"[iOS] 未找到数量+按钮，停留在当前数量: {self.udid}"
                )
                break

    async def _click_confirm_area(self):
        """
        点击票档选择页的"确定"/"下一步"按钮，进入购票人选择页。
        若按钮不存在（如直接跳转），则忽略。
        """
        await asyncio.sleep(0.3)

        confirm_btn = await self._wait_for_element(
            AppiumBy.IOS_PREDICATE,
            _PRED_CONFIRM,
            timeout=SHORT_WAIT
        )
        if confirm_btn:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, confirm_btn.click)
                logger.info(f"[iOS] 已点击确定/下一步: {self.udid}")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"[iOS] 点击确定按钮失败（已忽略）: {e}")
        else:
            logger.debug(f"[iOS] 未找到确定按钮，可能已自动跳转: {self.udid}")

    async def _select_buyer(
        self,
        buyer_name: Optional[str],
        quantity:   int,
    ) -> bool:
        """
        在购票人列表页选择实名购票人。
        - 若指定了 buyer_name，则精确匹配姓名
        - 否则按顺序勾选前 quantity 个购票人
        需要选 quantity 个购票人（实名制）。
        """
        # 等待购票人列表页出现
        buyer_list = await self._wait_for_element(
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeTableView" OR '
            'type == "XCUIElementTypeCollectionView"',
            timeout=NORMAL_WAIT
        )
        if not buyer_list:
            logger.warning(
                f"[iOS] 未出现购票人列表页（可能无需实名）: {self.udid}"
            )
            return True  # 无需选购票人，直接继续

        logger.info(f"[iOS] 进入购票人选择页: {self.udid}")
        await asyncio.sleep(0.5)

        try:
            loop = asyncio.get_running_loop()
            # 获取所有购票人条目
            cells = await self._find_elements(
                AppiumBy.IOS_CLASS_CHAIN,
                "**/XCUIElementTypeTableView/XCUIElementTypeCell"
            )
            if not cells:
                cells = await self._find_elements(
                    AppiumBy.IOS_CLASS_CHAIN,
                    "**/XCUIElementTypeCollectionView/XCUIElementTypeCell"
                )

            if not cells:
                logger.error(f"[iOS] 购票人列表为空: {self.udid}")
                return False

            selected_count = 0

            for cell in cells:
                if selected_count >= quantity:
                    break

                try:
                    # 获取该条目的文本（姓名）
                    labels = await loop.run_in_executor(
                        None,
                        lambda c=cell: c.find_elements(
                            AppiumBy.IOS_PREDICATE,
                            'type == "XCUIElementTypeStaticText"'
                        )
                    )
                    # 【性能优化5修复】使用 executor 访问 el.text
                    label_texts = []
                    for el in labels:
                        text = await loop.run_in_executor(None, lambda e=el: e.text if e.text else "")
                        label_texts.append(text)
                    cell_text = " ".join(label_texts)

                    # 按名称匹配
                    if buyer_name and buyer_name not in cell_text:
                        continue

                    # 检查是否已被勾选
                    checkbox = None
                    try:
                        checkbox = await loop.run_in_executor(
                            None,
                            lambda c=cell: c.find_element(
                                AppiumBy.IOS_PREDICATE,
                                'type == "XCUIElementTypeButton" AND '
                                '(name CONTAINS "check" OR name CONTAINS "select" '
                                'OR label CONTAINS "已选")'
                            )
                        )
                    except NoSuchElementException:
                        pass

                    is_checked = False
                    if checkbox:
                        # value == "1" 表示已勾选（iOS Checkbox 标准）
                        checkbox_value = await loop.run_in_executor(
                            None, lambda: checkbox.get_attribute("value")
                        )
                        is_checked = (checkbox_value == "1")

                    if not is_checked:
                        await loop.run_in_executor(None, cell.click)
                        logger.info(
                            f"[iOS] 已选购票人: {cell_text[:20]}: {self.udid}"
                        )
                        await asyncio.sleep(0.3)

                    selected_count += 1

                except Exception as e:
                    logger.debug(f"[iOS] 处理购票人条目异常: {e}")
                    continue

            if selected_count == 0:
                logger.error(
                    f"[iOS] 未能选中任何购票人 "
                    f"(buyer_name={buyer_name}): {self.udid}"
                )
                return False

            if selected_count < quantity:
                logger.warning(
                    f"[iOS] 仅选中 {selected_count}/{quantity} 个购票人: {self.udid}"
                )

            # 点击"确定"进入订单确认页
            await self._click_confirm_area()
            return True

        except Exception as e:
            logger.error(f"[iOS] 购票人选择异常 {self.udid}: {e}")
            return False

    async def _submit_order(self) -> bool:
        """
        在订单确认页点击"提交订单"/"立即支付"按钮。
        提交后等待支付页面出现，以确认订单已成功创建。
        """
        logger.info(f"[iOS] 等待订单确认页: {self.udid}")

        submit_btn = await self._wait_for_element(
            AppiumBy.IOS_PREDICATE,
            _PRED_SUBMIT,
            timeout=NORMAL_WAIT
        )
        if not submit_btn:
            logger.error(f"[iOS] 未找到提交订单按钮: {self.udid}")
            return False

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, submit_btn.click)
            logger.info(f"[iOS] 已点击提交订单: {self.udid}")
        except Exception as e:
            logger.error(f"[iOS] 点击提交订单失败 {self.udid}: {e}")
            return False

        # 等待支付页面出现（成功标志）
        # 支付页通常包含"支付宝"/"微信支付"/"银行卡"等选项
        pay_page = await self._wait_for_element(
            AppiumBy.IOS_PREDICATE,
            '(label CONTAINS "支付宝" OR label CONTAINS "微信" '
            'OR label CONTAINS "银行卡" OR label CONTAINS "收银台" '
            'OR label CONTAINS "待付款")',
            timeout=LONG_WAIT
        )
        if pay_page:
            logger.info(f"[iOS] ✅ 订单提交成功，已进入支付页: {self.udid}")
            return True

        # 兜底：检查是否出现"订单详情"页（部分场景跳过支付选择）
        order_detail = await self._wait_for_element(
            AppiumBy.IOS_PREDICATE,
            'label CONTAINS "订单详情" OR label CONTAINS "待付款"',
            timeout=SHORT_WAIT
        )
        if order_detail:
            logger.info(f"[iOS] ✅ 订单提交成功，已进入订单详情: {self.udid}")
            return True

        logger.warning(
            f"[iOS] 提交订单后未检测到支付页，请人工确认: {self.udid}"
        )
        return False  # 保守返回 False，触发上层重试

    # ══════════════════════════════════════════════════════════════
    # 元素查找 / 等待（私有辅助）
    # ══════════════════════════════════════════════════════════════

    # 【BUG修复6】将 _wait_for_element 改为 async 方法，避免返回未执行的协程
    async def _wait_for_element(
        self,
        by:      str,
        value:   str,
        timeout: int = NORMAL_WAIT,
    ):
        """
        等待元素出现并返回，超时返回 None（不抛异常）。
        使用 WebDriverWait + EC.presence_of_element_located。
        """
        loop = asyncio.get_running_loop()
        try:
            element = await loop.run_in_executor(
                None,
                lambda: WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
            )
            return element
        except TimeoutException:
            return None
        except Exception as e:
            logger.debug(f"[iOS] _wait_for_element 异常 by={by}: {e}")
            return None

    async def _wait_for_clickable(
        self,
        by:      str,
        value:   str,
        timeout: int = NORMAL_WAIT,
    ):
        """
        等待元素出现且可点击（enabled & displayed），超时返回 None。
        """
        loop = asyncio.get_running_loop()
        try:
            element = await loop.run_in_executor(
                None,
                lambda: WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by, value))
                )
            )
            return element
        except TimeoutException:
            return None
        except Exception as e:
            logger.debug(f"[iOS] _wait_for_clickable 异常 by={by}: {e}")
            return None

    async def _find_element(self, by: str, value: str):
        """
        立即查找单个元素，未找到返回 None（不抛异常）。
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                lambda: self.driver.find_element(by, value)
            )
        except NoSuchElementException:
            return None
        except Exception as e:
            logger.debug(f"[iOS] _find_element 异常 by={by}: {e}")
            return None

    async def _find_elements(self, by: str, value: str) -> list:
        """
        立即查找所有匹配元素，未找到返回空列表（不抛异常）。
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                lambda: self.driver.find_elements(by, value)
            )
        except Exception as e:
            logger.debug(f"[iOS] _find_elements 异常 by={by}: {e}")
            return []

    # ══════════════════════════════════════════════════════════════
    # 业务判断辅助（私有）
    # ══════════════════════════════════════════════════════════════

    async def _is_element_sold_out(self, element) -> bool:
        """
        判断票档元素是否处于售罄/不可购买状态。
        检测维度：
          1. 元素 enabled 属性为 false
          2. 文本包含"售罄"/"暂无"/"缺货"/"已售完"
          3. 子元素中存在售罄标记
        """
        try:
            loop = asyncio.get_running_loop()
            # 维度1：enabled 属性
            enabled = await loop.run_in_executor(None, lambda: element.get_attribute("enabled"))
            if enabled == "false":
                return True

            # 维度2：自身文本
            own_text = await loop.run_in_executor(None, lambda: element.text) or ""
            sold_out_keywords = ("售罄", "暂无", "缺货", "已售完", "停售")
            if any(kw in own_text for kw in sold_out_keywords):
                return True

            # 维度3：子元素文本
            children = await loop.run_in_executor(
                None,
                lambda: element.find_elements(
                    AppiumBy.IOS_PREDICATE,
                    'type == "XCUIElementTypeStaticText"'
                )
            )
            for child in children:
                child_text = await loop.run_in_executor(None, lambda: child.text) or ""
                if any(kw in child_text for kw in sold_out_keywords):
                    return True

        except Exception:
            pass  # 元素已失效，保守认为不售罄（让后续点击失败来处理）
        return False

    @staticmethod
    def _parse_price(text: str) -> Optional[int]:
        """
        从票档文本中提取价格（元，整数）。
        支持格式：¥380、380元、380.00、¥380.00
        返回 None 表示未找到价格。
        """
        # 匹配 ¥ 或 元 附近的数字
        patterns = [
            r'[¥￥]\s*(\d+(?:\.\d+)?)',   # ¥380 / ¥380.00
            r'(\d+(?:\.\d+)?)\s*元',       # 380元
            r'(\d+(?:\.\d+)?)\s*\/张',     # 380/张
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return int(float(match.group(1)))
                except ValueError:
                    continue
        return None

    # ══════════════════════════════════════════════════════════════
    # 页面操作辅助（私有）
    # ══════════════════════════════════════════════════════════════

    async def _dismiss_popup(self):
        """
        关闭可能遮挡主流程的弹窗（广告、活动提示、权限请求等）。
        iOS 弹窗分两类：
          1. 系统 Alert（权限请求）→ 通过 switch_to.alert 处理
          2. APP 内自定义弹窗     → 通过 Predicate 查找关闭按钮
        """
        loop = asyncio.get_running_loop()
        # ── 处理系统 Alert ─────────────────────────────────────
        try:
            alert = await loop.run_in_executor(None, lambda: self.driver.switch_to.alert)
            alert_text = await loop.run_in_executor(None, lambda: alert.text) or ""
            # 对于权限请求，选择"允许"；对于其他提示，选择"确定"
            if any(kw in alert_text for kw in ("通知", "位置", "相机", "麦克风")):
                # 权限弹窗：点击"允许"（第二个按钮）
                await loop.run_in_executor(None, alert.accept)
            else:
                # 普通提示：点击"确定"
                await loop.run_in_executor(None, alert.accept)
            logger.debug(f"[iOS] 已关闭系统 Alert: {alert_text[:30]}")
            await asyncio.sleep(0.3)
            return
        except Exception:
            pass  # 无系统 Alert

        # ── 处理 APP 内自定义弹窗 ─────────────────────────────
        close_btn = await self._find_element(
            AppiumBy.IOS_PREDICATE,
            _PRED_POPUP_CLOSE
        )
        if close_btn:
            try:
                await loop.run_in_executor(None, close_btn.click)
                logger.debug(f"[iOS] 已关闭 APP 内弹窗: {self.udid}")
                await asyncio.sleep(0.3)
            except Exception:
                pass

    async def _scroll_down(self, distance: int = 300):
        """
        向下滚动页面（手指向上滑动）。
        使用 mobile: scroll 脚本，比 TouchAction 更稳定。
        :param distance: 滚动像素距离（逻辑像素）
        """
        loop = asyncio.get_running_loop()
        try:
            # 【性能优化6修复】方式1：mobile: scroll（推荐，适合 ScrollView/TableView）
            # 使用更合理的比例 distance / 1000
            await loop.run_in_executor(
                None,
                lambda: self.driver.execute_script(
                    "mobile: scroll",
                    {"direction": "down", "distance": distance / 1000}
                    # distance 参数为屏幕高度的倍数（0.0~1.0+）
                )
            )
        except Exception:
            try:
                # 【BUG-I3修复】方式2：mobile: swipe（更通用），删除无用的 size 变量
                await loop.run_in_executor(
                    None,
                    lambda: self.driver.execute_script(
                        "mobile: swipe",
                        {
                            "direction": "up",
                            "velocity": 1500,   # 像素/秒
                        }
                    )
                )
            except Exception as e:
                logger.debug(f"[iOS] 滚动失败: {e}")

    async def _swipe_back(self):
        """
        iOS 右滑返回（从屏幕左边缘向右滑动）。
        等效于点击导航栏"返回"按钮。
        """
        loop = asyncio.get_running_loop()
        try:
            size = await loop.run_in_executor(None, self.driver.get_window_size)
            h    = size["height"]
            mid_y = h // 2
            await loop.run_in_executor(
                None,
                lambda: self.driver.execute_script(
                    "mobile: dragFromToForDuration",
                    {
                        "fromX": 5,
                        "fromY": mid_y,
                        "toX":   150,
                        "toY":   mid_y,
                        "duration": 0.4,
                    }
                )
            )
            logger.debug(f"[iOS] 右滑返回: {self.udid}")
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.debug(f"[iOS] 右滑返回失败: {e}")

    # ══════════════════════════════════════════════════════════════
    # 公开工具方法
    # ══════════════════════════════════════════════════════════════

    async def take_screenshot(self, save_path: Optional[str] = None) -> Union[bytes, None]:
        """
        截取当前屏幕截图。
        :param save_path: 若指定则保存为 PNG 文件，同时返回原始字节
        :return: PNG 字节数据，失败返回 None
        """
        if self.driver is None:
            logger.error("设备未连接")
            return None
        if not self._check_driver():
            return None
        try:
            loop = asyncio.get_running_loop()
            png_bytes = await loop.run_in_executor(None, self.driver.get_screenshot_as_png)
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(png_bytes)
                logger.info(f"[iOS] 截图已保存: {save_path}")
            return png_bytes
        except Exception as e:
            logger.error(f"[iOS] 截图失败 {self.udid}: {e}")
            return None

    async def get_current_page_source(self) -> str:
        """
        获取当前页面的 XML 源码（用于调试 / 元素定位分析）。
        注意：iOS 页面源码可能较大（>1MB），建议仅在调试时调用。
        """
        if self.driver is None:
            logger.error("设备未连接")
            return ""
        if not self._check_driver():
            return ""
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: self.driver.page_source)
        except Exception as e:
            logger.error(f"[iOS] 获取页面源码失败 {self.udid}: {e}")
            return ""

    async def press_home(self):
        """
        按下 Home 键，将 APP 切换到后台。
        iOS 没有实体 Home 键（iPhone X 以后），使用 Appium 模拟。
        """
        if self.driver is None:
            logger.error("设备未连接")
            return
        if not self._check_driver():
            return
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.driver.execute_script("mobile: pressButton", {"name": "home"})
            )
            logger.info(f"[iOS] 已按 Home 键: {self.udid}")
        except Exception as e:
            logger.warning(f"[iOS] 按 Home 键失败 {self.udid}: {e}")

    async def lock_screen(self, seconds: int = 0):
        """
        锁定屏幕（可选延迟解锁）。
        :param seconds: 0 表示仅锁定不自动解锁
        """
        if self.driver is None:
            logger.error("设备未连接")
            return
        if not self._check_driver():
            return
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: self.driver.lock(seconds))
            logger.info(f"[iOS] 屏幕已锁定: {self.udid}")
        except Exception as e:
            logger.warning(f"[iOS] 锁屏失败 {self.udid}: {e}")

    async def unlock_screen(self):
        """解锁屏幕（仅适用于无密码设备）。"""
        if self.driver is None:
            logger.error("设备未连接")
            return
        if not self._check_driver():
            return
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.driver.unlock)
            logger.info(f"[iOS] 屏幕已解锁: {self.udid}")
        except Exception as e:
            logger.warning(f"[iOS] 解锁失败 {self.udid}: {e}")

    # ══════════════════════════════════════════════════════════════
    # 内部守卫方法
    # ══════════════════════════════════════════════════════════════

    def _check_driver(self) -> bool:
        """
        检查 Appium driver 是否可用。
        若未连接则记录错误并返回 False。
        """
        if not self._connected or self.driver is None:
            logger.error(
                f"[iOS] driver 未初始化，请先调用 connect(): {self.udid}"
            )
            return False
        return True

    @staticmethod
    def _is_stopped(stop_event: Optional[threading.Event]) -> bool:
        """检查外部停止信号是否已触发。"""
        return stop_event is not None and stop_event.is_set()

    # ══════════════════════════════════════════════════════════════
    # dunder
    # ══════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return (
            f"<IOSDriver udid={self.udid[:8]}… "
            f"server={self.appium_server} "
            f"wda_port={self.wda_port} "
            f"status={status}>"
        )

    # 【BUG修复5】将同步上下文管理器改为异步版本
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False  # 不吞异常


# ══════════════════════════════════════════════════════════════════
# 自测入口（python ios_driver.py 直接运行）
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── 从命令行读取参数，或使用默认值 ──────────────────────────
    # 用法：python ios_driver.py <udid> [appium_url] [wda_port]
    _udid          = sys.argv[1] if len(sys.argv) > 1 else "auto"
    _appium_server = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:4723"
    _wda_port      = int(sys.argv[3]) if len(sys.argv) > 3 else 8100

    # 若 udid == "auto"，尝试通过 idevice_id 自动发现第一台设备
    if _udid == "auto":
        try:
            _result = subprocess.run(
                "idevice_id -l", shell=True,
                capture_output=True, text=True, timeout=5
            )
            _lines = [l.strip() for l in _result.stdout.splitlines() if l.strip()]
            if _lines:
                _udid = _lines[0]
                logger.info(f"自动发现设备: {_udid}")
            else:
                logger.error("未发现已连接的 iOS 设备，请用 USB 连接后重试")
                sys.exit(1)
        except Exception as _e:
            logger.error(f"idevice_id 调用失败: {_e}（请安装 libimobiledevice）")
            sys.exit(1)

    logger.info(
        f"=== iOS Driver 自测开始 ===\n"
        f"  UDID         : {_udid}\n"
        f"  Appium Server: {_appium_server}\n"
        f"  WDA Port     : {_wda_port}\n"
    )

    # ── 构造驱动实例 ─────────────────────────────────────────────
    driver = IOSDriver(
        udid=_udid,
        appium_server=_appium_server,
        wda_port=_wda_port,
        # 可按需覆盖 bundle_id，默认为大麦 APP
        # bundle_id="com.taobao.damai",
    )

    async def run_test():
        # ── 测试1：连接 ──────────────────────────────────────────────
        logger.info("── 测试1：连接设备 ──")
        ok = await driver.connect()
        if not ok:
            logger.error("连接失败，退出自测")
            sys.exit(1)
        logger.info(f"连接成功: {driver}")

        try:
            # ── 测试2：截图 ──────────────────────────────────────────
            logger.info("── 测试2：截图 ──")
            screenshot_path = f"screenshot_{_udid[:8]}.png"
            png = await driver.take_screenshot(save_path=screenshot_path)
            if png:
                logger.info(f"截图成功，大小: {len(png):,} bytes → {screenshot_path}")
            else:
                logger.warning("截图失败")

            # ── 测试3：获取页面源码（仅打印前 500 字符）────────────
            logger.info("── 测试3：页面源码 ──")
            source = await driver.get_current_page_source()
            if source:
                logger.info(f"页面源码长度: {len(source):,} chars")
                logger.debug(f"源码前 500 字符:\n{source[:500]}")
            else:
                logger.warning("获取页面源码失败")

            # ── 测试4：弹窗关闭（无弹窗时静默忽略）────────────────
            logger.info("── 测试4：关闭弹窗 ──")
            await driver._dismiss_popup()
            logger.info("弹窗检测完毕（无弹窗时正常）")

            # ── 测试5：模拟抢票流程（需要提前在 APP 内打开演出详情页）
            logger.info("── 测试5：模拟抢票（请在手机上打开演出详情页后按回车）──")
            input(">>> 请在手机上手动打开目标演出详情页，然后按回车继续...")

            # 构造测试用停止事件（不触发，让流程跑完）
            _stop_event = threading.Event()

            result = await driver.rush_ticket(
                event_url="",           # 已在详情页，无需导航
                target_price=None,      # None = 不限价格，选第一个可购买票档
                quantity=1,
                buyer_name=None,        # None = 选第一个购票人
                stop_event=_stop_event,
            )

            if result:
                logger.info("✅ 抢票流程执行成功（请在手机上确认支付页面）")
            else:
                logger.warning("❌ 抢票流程未成功（可能票已售罄或页面状态不符）")

            # ── 测试6：再次截图，记录最终状态 ───────────────────────
            logger.info("── 测试6：最终状态截图 ──")
            final_path = f"screenshot_{_udid[:8]}_final.png"
            await driver.take_screenshot(save_path=final_path)
            logger.info(f"最终截图已保存: {final_path}")

        except KeyboardInterrupt:
            logger.info("用户中断自测")

        except Exception as _e:
            logger.exception(f"自测过程中发生未预期异常: {_e}")

        finally:
            # ── 断开连接 ─────────────────────────────────────────────
            logger.info("── 断开连接 ──")
            await driver.disconnect()
            logger.info("=== iOS Driver 自测结束 ===")

    asyncio.run(run_test())

