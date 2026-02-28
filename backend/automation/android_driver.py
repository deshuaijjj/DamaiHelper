"""
android_driver.py
Android 设备驱动 —— 基于 Appium 控制大麦 APP 完成抢票流程
"""

import asyncio
import logging
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

# ── 大麦 APP 基本信息 ──────────────────────────────────────────
DAMAI_PACKAGE  = "cn.damai"
DAMAI_ACTIVITY = "cn.damai.homepage.SplashActivity"

# ── 默认超时（秒） ─────────────────────────────────────────────
SHORT_WAIT  = 3
NORMAL_WAIT = 10
LONG_WAIT   = 30


class AndroidDriver:
    """
    封装单台 Android 设备的所有操作。
    每台设备对应一个实例，由 DeviceManager 统一管理。
    """

    def __init__(self, device_id: str, appium_server: str = "http://127.0.0.1:4723"):
        self.device_id     = device_id
        self.appium_server = appium_server
        self.driver: Optional[webdriver.Remote] = None
        self._connected    = False

    # ══════════════════════════════════════════════════════════════
    # 连接 / 断开
    # ══════════════════════════════════════════════════════════════

    async def connect(self) -> bool:
        """初始化 Appium 会话，连接设备。"""
        try:
            loop = asyncio.get_running_loop()
            
            def _connect():
                options = AppiumOptions()
                options.platform_name = "Android"
                options.set_capability("appium:deviceName",          self.device_id)
                options.set_capability("appium:udid",                self.device_id)
                options.set_capability("appium:appPackage",          DAMAI_PACKAGE)
                options.set_capability("appium:appActivity",         DAMAI_ACTIVITY)
                options.set_capability("appium:noReset",             True)
                options.set_capability("appium:autoGrantPermissions",True)
                options.set_capability("appium:newCommandTimeout",   300)
                options.set_capability("appium:androidDeviceReadyTimeout", 30)
                options.set_capability("appium:skipServerInstallation", True)
                options.set_capability("appium:skipDeviceInitialization", True)
                return webdriver.Remote(self.appium_server, options=options)
            
            self.driver = await loop.run_in_executor(None, _connect)
            self._connected = True
            logger.info(f"[Android] 设备连接成功: {self.device_id}")
            return True
        except WebDriverException as e:
            logger.error(f"[Android] 设备连接失败 {self.device_id}: {e}")
            return False

    async def disconnect(self):
        """释放 Appium 会话资源。"""
        if self.driver:
            try:
                loop = asyncio.get_running_loop()
                # 【BUG修复4】使用正确的 quit() 方法关闭驱动，而非不存在的 session().close()
                await loop.run_in_executor(None, self.driver.quit)
                logger.info(f"[Android] 设备已断开: {self.device_id}")
            except Exception as e:
                logger.warning(f"[Android] 断开时出现异常（已忽略）{self.device_id}: {e}")
            finally:
                self.driver     = None
                self._connected = False

    # ══════════════════════════════════════════════════════════════
    # 设备信息
    # ══════════════════════════════════════════════════════════════

    async def get_device_info(self) -> dict:
        """
        通过 ADB 获取设备基本信息。
        不依赖 Appium，设备未连接 Appium 时也可调用。
        """
        info = {
            "device_id":   self.device_id,
            "platform":    "android",
            "model":       None,
            "brand":       None,  # 【关键问题2修复】添加 brand 字段
            "name":        None,  # 【关键问题2修复】添加 name 字段（设备名称）
            "version":     None,  # 【关键问题2修复】改为 version（与前端一致）
            "battery":     -1,
            "screen_size": None,
        }
        try:
            loop = asyncio.get_running_loop()
            info["model"] = await loop.run_in_executor(
                None, lambda: self._adb_shell("getprop ro.product.model")
            )
            # 【关键问题2修复】获取 brand 信息
            info["brand"] = await loop.run_in_executor(
                None, lambda: self._adb_shell("getprop ro.product.brand")
            )
            # 【关键问题2修复】获取设备名称
            info["name"] = await loop.run_in_executor(
                None, lambda: self._adb_shell("getprop ro.product.name")
            )
            # 【关键问题2修复】改为 version 字段
            info["version"] = await loop.run_in_executor(
                None, lambda: self._adb_shell("getprop ro.build.version.release")
            )
            # 电量：dumpsys battery | grep level
            battery_raw = await loop.run_in_executor(
                None, lambda: self._adb_shell("dumpsys battery | grep level")
            )
            if battery_raw:
                # 【BUG-A3修复】添加异常保护，防止解析失败
                try:
                    info["battery"] = int(battery_raw.split(":")[-1].strip())
                except (ValueError, IndexError):
                    info["battery"] = -1

            # 分辨率：wm size → "Physical size: 1080x2400"
            size_raw = await loop.run_in_executor(
                None, lambda: self._adb_shell("wm size")
            )
            if size_raw and ":" in size_raw:
                info["screen_size"] = size_raw.split(":")[-1].strip()
        except Exception as e:
            logger.warning(f"[Android] 获取设备信息部分失败 {self.device_id}: {e}")
        return info

    def _adb_shell(self, cmd: str) -> str:
        """执行 adb shell 命令并返回 stdout 字符串（去除首尾空白）。"""
        result = subprocess.run(
            f"adb -s {self.device_id} shell {cmd}",
            shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()

    # ══════════════════════════════════════════════════════════════
    # APP 操作
    # ══════════════════════════════════════════════════════════════

    async def start_app(self) -> bool:
        """
        启动大麦 APP，等待主页加载完成。
        若 APP 已在前台则跳过重复启动。
        """
        if self.driver is None:
            logger.error("设备未连接")
            return False
        if not self._check_driver():
            return False
        try:
            loop = asyncio.get_running_loop()
            current_pkg = await loop.run_in_executor(None, lambda: self.driver.current_package)
            if current_pkg == DAMAI_PACKAGE:
                logger.info(f"[Android] 大麦 APP 已在前台: {self.device_id}")
                return True

            await loop.run_in_executor(None, lambda: self.driver.activate_app(DAMAI_PACKAGE))
            # 【BUG-A1修复】等待首页 Tab 栏出现，检查返回值而非捕获异常
            tab_bar = await self._wait_for_element(
                AppiumBy.XPATH,
                '//*[@resource-id="cn.damai:id/home_tab_bar"]',
                timeout=LONG_WAIT
            )
            if tab_bar:
                logger.info(f"[Android] 大麦 APP 启动成功: {self.device_id}")
                return True
            logger.error(f"[Android] 大麦 APP 启动超时: {self.device_id}")
            return False
        except Exception as e:
            logger.error(f"[Android] 启动 APP 异常 {self.device_id}: {e}")
            return False

    async def navigate_to_event(self, event_url: str) -> bool:
        """
        导航到演出详情页并等待页面加载完成。
        用于抢票前30秒预热，让页面提前就绪。
        """
        if self.driver is None:
            logger.error("设备未连接")
            return False
        if not self._check_driver():
            return False
        try:
            loop = asyncio.get_running_loop()
            logger.info(f"[Android] 导航到演出页: {self.device_id} → {event_url}")
            # 通过 URL Scheme 跳转（大麦支持 damai:// 协议）
            await loop.run_in_executor(None, lambda: self.driver.get(event_url))
            await asyncio.sleep(1)

            # 等待"立即购买"或"即将开抢"按钮出现，说明详情页已加载
            buy_btn = await self._wait_for_element(
                AppiumBy.XPATH,
                '//*[contains(@text,"立即购买") or contains(@text,"即将开抢") '
                'or contains(@text,"等待购买") or contains(@text,"暂时缺货")]',
                timeout=NORMAL_WAIT
            )
            if buy_btn:
                logger.info(f"[Android] 演出页加载完成: {self.device_id}")
                return True
            logger.warning(f"[Android] 演出页加载超时，未找到购买按钮: {self.device_id}")
            return False
        except Exception as e:
            logger.error(f"[Android] 导航演出页异常 {self.device_id}: {e}")
            return False

    # ══════════════════════════════════════════════════════════════
    # 核心抢票流程
    # ══════════════════════════════════════════════════════════════

    async def rush_ticket(
        self,
        event_url:      str,
        preferred_area: Optional[str]            = None,
        target_price:   Optional[int]            = None,
        quantity:       int                      = 1,
        buyer_name:     Optional[str]            = None,
        stop_event:     Optional[threading.Event] = None,
    ) -> bool:
        """
        完整抢票流程：
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
            f"[Android] 开始抢票 device={self.device_id} "
            f"area={preferred_area} price≤{target_price} qty={quantity}"
        )

        try:
            # 导航到演出详情页
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, 
                lambda: subprocess.run(
                    f"adb -s {self.device_id} shell am start -a android.intent.action.VIEW -d '{event_url}'",
                    shell=True, capture_output=True, text=True, timeout=10
                )
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
                        logger.warning(f"[Android] 点击购买按钮失败，重试 {attempt + 1}/{max_retries}")
                        await asyncio.sleep(retry_interval)
                        continue
                    else:
                        logger.error(f"[Android] 点击购买按钮失败，已达最大重试次数")
                        return False
                break

            # ── Step 2: 选择票档 ────────────────────────────────
            if self._is_stopped(stop_event):
                return False

            if not await self._select_ticket_area(preferred_area, target_price, stop_event):
                logger.error(f"[Android] 票档选择失败: {self.device_id}")
                return False

            # ── Step 3: 选择数量 ────────────────────────────────
            if self._is_stopped(stop_event):
                return False

            await self._select_quantity(quantity)

            # ── Step 4: 点击"确定" / 进入下一步 ─────────────────
            if self._is_stopped(stop_event):
                return False

            await self._click_confirm_area()

            # ── Step 5: 选择购票人 ──────────────────────────────
            if self._is_stopped(stop_event):
                return False

            if not await self._select_buyer(buyer_name, quantity):
                logger.error(f"[Android] 购票人选择失败: {self.device_id}")
                return False

            # ── Step 6: 提交订单 ────────────────────────────────
            if self._is_stopped(stop_event):
                return False

            if not await self._submit_order():
                return False

            logger.info(f"[Android] 🎉 抢票成功！device={self.device_id}")
            return True

        except Exception as e:
            logger.error(f"[Android] 抢票流程异常 {self.device_id}: {e}")
            return False

    # ══════════════════════════════════════════════════════════════
    # 抢票子步骤（私有）
    # ══════════════════════════════════════════════════════════════

    async def _click_buy_button(self, stop_event: Optional[threading.Event]) -> bool:
        """
        等待并点击"立即购买"按钮。
        开票前按钮可能是灰色/倒计时，循环等待直到可点击或被停止。
        """
        logger.info(f"[Android] 等待购买按钮激活: {self.device_id}")
        loop = asyncio.get_running_loop()
        deadline = time.time() + 60  # 最多等60秒
        while time.time() < deadline:
            if self._is_stopped(stop_event):
                return False
            try:
                btn = await loop.run_in_executor(
                    None,
                    lambda: self.driver.find_element(
                        AppiumBy.XPATH,
                        '//*[contains(@text,"立即购买") and @clickable="true"]'
                    )
                )
                await loop.run_in_executor(None, btn.click)
                logger.info(f"[Android] 已点击立即购买: {self.device_id}")
                await asyncio.sleep(0.5)
                return True
            except NoSuchElementException:
                await asyncio.sleep(0.1)  # 100ms 轮询
        logger.error(f"[Android] 等待购买按钮超时: {self.device_id}")
        return False

    async def _select_ticket_area(
        self,
        preferred_area: Optional[str],
        target_price:   Optional[int],
        stop_event:     Optional[threading.Event],
    ) -> bool:
        """
        在票档选择页选择合适的票档。
        优先级：preferred_area > target_price（最低价且≤target_price） > 第一个可购买票档
        """
        # 【BUG-A1修复】等待票档列表出现，检查返回值而非捕获异常
        ticket_list = await self._wait_for_element(
            AppiumBy.XPATH,
            '//*[@resource-id="cn.damai:id/ticket_area_list"]',
            timeout=NORMAL_WAIT
        )
        if not ticket_list:
            logger.error(f"[Android] 票档列表未出现: {self.device_id}")
            return False

        if self._is_stopped(stop_event):
            return False

        try:
            loop = asyncio.get_running_loop()
            # 获取所有票档条目
            items = await loop.run_in_executor(
                None,
                lambda: self.driver.find_elements(
                    AppiumBy.XPATH,
                    '//*[@resource-id="cn.damai:id/ticket_area_item"]'
                )
            )
            if not items:
                # 兜底：只有一个票档，直接进入下一步
                logger.info(f"[Android] 未找到票档列表，可能只有单一票档: {self.device_id}")
                return True

            selected = None

            # 1. 按名称匹配
            if preferred_area:
                for item in items:
                    try:
                        name_el = await loop.run_in_executor(
                            None,
                            lambda i=item: i.find_element(
                                AppiumBy.XPATH, './/*[@resource-id="cn.damai:id/ticket_area_name"]'
                            )
                        )
                        price_el = await loop.run_in_executor(
                            None,
                            lambda i=item: i.find_element(
                                AppiumBy.XPATH, './/*[@resource-id="cn.damai:id/ticket_area_price"]'
                            )
                        )
                        sold_out = await self._is_element_sold_out(item)
                        name_text = await loop.run_in_executor(None, lambda: name_el.text)
                        price_text = await loop.run_in_executor(None, lambda: price_el.text)
                        if preferred_area in name_text and not sold_out:
                            selected = item
                            logger.info(f"[Android] 按名称匹配票档: {name_text} {price_text}")
                            break
                    except NoSuchElementException:
                        continue

            # 2. 按价格筛选（≤target_price 中最低价）
            if not selected and target_price is not None:
                best_price = None
                best_item  = None
                for item in items:
                    try:
                        price_el  = await loop.run_in_executor(
                            None,
                            lambda i=item: i.find_element(
                                AppiumBy.XPATH, './/*[@resource-id="cn.damai:id/ticket_area_price"]'
                            )
                        )
                        sold_out  = await self._is_element_sold_out(item)
                        price_text = await loop.run_in_executor(None, lambda: price_el.text)
                        price_val = self._parse_price(price_text)
                        if price_val and price_val <= target_price and not sold_out:
                            if best_price is None or price_val < best_price:
                                best_price = price_val
                                best_item  = item
                    except NoSuchElementException:
                        continue
                if best_item:
                    selected = best_item
                    logger.info(f"[Android] 按价格匹配票档: ¥{best_price}")

            # 3. 兜底：选第一个可购买的票档
            if not selected:
                for item in items:
                    if not await self._is_element_sold_out(item):
                        selected = item
                        logger.info(f"[Android] 兜底选择第一个可购买票档")
                        break

            if not selected:
                logger.error(f"[Android] 没有可购买的票档: {self.device_id}")
                return False

            await loop.run_in_executor(None, selected.click)
            await asyncio.sleep(0.3)
            return True

        except Exception as e:
            logger.error(f"[Android] 票档选择异常 {self.device_id}: {e}")
            return False

    async def _select_quantity(self, quantity: int):
        """调整购票数量到指定值（默认1张，最多通过点击"+"增加）。"""
        try:
            loop = asyncio.get_running_loop()
            # 当前数量
            qty_el = await self._find_element(
                AppiumBy.XPATH,
                '//*[@resource-id="cn.damai:id/ticket_count"]'
            )
            if not qty_el:
                return
            qty_text = await loop.run_in_executor(None, lambda: qty_el.text)
            current = int(qty_text.strip()) if qty_text.strip().isdigit() else 1
            plus_btn = await self._find_element(
                AppiumBy.XPATH,
                '//*[@resource-id="cn.damai:id/ticket_count_add"]'
            )
            if plus_btn:
                for _ in range(quantity - current):
                    await loop.run_in_executor(None, plus_btn.click)
                    await asyncio.sleep(0.1)
            logger.info(f"[Android] 数量已设置为 {quantity}: {self.device_id}")
        except Exception as e:
            logger.warning(f"[Android] 数量调整失败（使用默认值）{self.device_id}: {e}")

    async def _click_confirm_area(self):
        """点击票档选择页的"确定"按钮，进入购票人选择页。"""
        try:
            btn = await self._wait_for_element(
                AppiumBy.XPATH,
                '//*[contains(@text,"确定") or contains(@text,"下一步")]',
                timeout=SHORT_WAIT
            )
            if btn:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, btn.click)
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning(f"[Android] 点击确定按钮失败 {self.device_id}: {e}")

    async def _select_buyer(self, buyer_name: Optional[str], quantity: int) -> bool:
        """
        在购票人选择页选择购票人。
        若指定 buyer_name 则精确匹配，否则按顺序选前 quantity 个。
        """
        # 【BUG-A1修复】等待购票人列表，检查返回值而非捕获异常
        buyer_list = await self._wait_for_element(
            AppiumBy.XPATH,
            '//*[@resource-id="cn.damai:id/buyer_list"]',
            timeout=NORMAL_WAIT
        )
        if not buyer_list:
            # 可能不需要选购票人（演出未要求实名）
            logger.info(f"[Android] 未出现购票人列表，跳过: {self.device_id}")
            return True

        try:
            loop = asyncio.get_running_loop()
            buyers = await loop.run_in_executor(
                None,
                lambda: self.driver.find_elements(
                    AppiumBy.XPATH,
                    '//*[@resource-id="cn.damai:id/buyer_item"]'
                )
            )
            if not buyers:
                logger.warning(f"[Android] 购票人列表为空: {self.device_id}")
                return False

            selected_count = 0
            for buyer in buyers:
                if selected_count >= quantity:
                    break
                try:
                    name_el = await loop.run_in_executor(
                        None,
                        lambda b=buyer: b.find_element(
                            AppiumBy.XPATH, './/*[@resource-id="cn.damai:id/buyer_name"]'
                        )
                    )
                    name_text = await loop.run_in_executor(None, lambda: name_el.text)
                    if buyer_name and buyer_name not in name_text:
                        continue
                    await loop.run_in_executor(None, buyer.click)
                    selected_count += 1
                    logger.info(f"[Android] 已选购票人: {name_text}")
                    await asyncio.sleep(0.2)
                except NoSuchElementException:
                    continue

            if selected_count == 0:
                logger.error(f"[Android] 未能选到购票人: {self.device_id}")
                return False

            # 点击"确认"进入订单页
            confirm = await self._wait_for_element(
                AppiumBy.XPATH,
                '//*[contains(@text,"确认") or contains(@text,"下一步")]',
                timeout=SHORT_WAIT
            )
            if confirm:
                await loop.run_in_executor(None, confirm.click)
                await asyncio.sleep(0.5)
            return True

        except Exception as e:
            logger.error(f"[Android] 购票人选择异常 {self.device_id}: {e}")
            return False

    async def _submit_order(self) -> bool:
        """在订单确认页点击"提交订单"。"""
        try:
            btn = await self._wait_for_element(
                AppiumBy.XPATH,
                '//*[contains(@text,"提交订单") or contains(@text,"立即支付")]',
                timeout=NORMAL_WAIT
            )
            if not btn:
                logger.error(f"[Android] 未找到提交订单按钮: {self.device_id}")
                return False
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, btn.click)
            await asyncio.sleep(1)

            # 判断是否进入支付页（成功）或弹出失败提示
            success = await self._wait_for_element(
                AppiumBy.XPATH,
                '//*[contains(@text,"支付") or contains(@text,"付款")]',
                timeout=NORMAL_WAIT
            )
            if success:
                logger.info(f"[Android] 订单已提交，进入支付页: {self.device_id}")
                return True

            # 检查是否有错误提示
            error = await self._find_element(
                AppiumBy.XPATH,
                '//*[contains(@text,"库存不足") or contains(@text,"已售罄") '
                'or contains(@text,"网络") or contains(@text,"失败")]'
            )
            if error:
                error_text = await loop.run_in_executor(None, lambda: error.text)
                logger.warning(f"[Android] 提交订单失败: {error_text} | {self.device_id}")
            return False

        except Exception as e:
            logger.error(f"[Android] 提交订单异常 {self.device_id}: {e}")
            return False

    # ══════════════════════════════════════════════════════════════
    # 工具方法（私有）
    # ══════════════════════════════════════════════════════════════

    def _check_driver(self) -> bool:
        """检查 Appium driver 是否可用。"""
        if not self.driver or not self._connected:
            logger.error(f"[Android] Driver 未初始化，请先调用 connect(): {self.device_id}")
            return False
        return True

    def _is_stopped(self, stop_event: Optional[threading.Event]) -> bool:
        """检查是否收到停止信号。"""
        if stop_event and stop_event.is_set():
            logger.info(f"[Android] 收到停止信号，退出抢票: {self.device_id}")
            return True
        return False

    # 【BUG修复6】将 _wait_for_element 改为 async 方法，避免返回未执行的协程
    async def _wait_for_element(
        self,
        by:      str,
        value:   str,
        timeout: int = NORMAL_WAIT,
    ):
        """
        等待元素出现并返回，超时返回 None（不抛异常）。
        内部使用 WebDriverWait + EC.presence_of_element_located。
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
            logger.debug(f"[Android] 等待元素超时 by={by} value={value}")
            return None
        except WebDriverException as e:
            logger.debug(f"[Android] 等待元素异常 by={by} value={value}: {e}")
            return None

    async def _wait_for_clickable(
        self,
        by:      str,
        value:   str,
        timeout: int = NORMAL_WAIT,
    ):
        """
        等待元素可点击并返回，超时返回 None。
        比 _wait_for_element 更严格，确保按钮真正可交互。
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
            logger.debug(f"[Android] 等待可点击元素超时 by={by} value={value}")
            return None
        except WebDriverException as e:
            logger.debug(f"[Android] 等待可点击元素异常 by={by} value={value}: {e}")
            return None

    async def _find_element(self, by: str, value: str):
        """
        立即查找元素，未找到返回 None（不抛异常）。
        适用于不需要等待的场景（如检测弹窗、错误提示）。
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                lambda: self.driver.find_element(by, value)
            )
        except NoSuchElementException:
            return None
        except WebDriverException as e:
            logger.debug(f"[Android] find_element 异常 by={by} value={value}: {e}")
            return None

    async def _find_elements(self, by: str, value: str) -> list:
        """
        立即查找所有匹配元素，失败返回空列表。
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                lambda: self.driver.find_elements(by, value)
            )
        except WebDriverException as e:
            logger.debug(f"[Android] find_elements 异常 by={by} value={value}: {e}")
            return []

    async def _is_element_sold_out(self, element) -> bool:
        """
        判断某个票档条目是否已售罄或不可购买。
        检测策略：
          1. 查找子元素中含"售罄"/"暂无"/"缺货"文字
          2. 检查条目整体的 enabled 属性
          3. 检查条目的 alpha（透明度）属性（灰色通常表示不可选）
        """
        try:
            loop = asyncio.get_running_loop()
            # 策略1：文字检测
            sold_out_keywords = ["售罄", "暂无", "缺货", "已售完", "无票"]
            try:
                texts = await loop.run_in_executor(
                    None,
                    lambda: element.find_elements(AppiumBy.XPATH, ".//*[@text]")
                )
                for t in texts:
                    text_content = await loop.run_in_executor(None, lambda: t.text)
                    if any(kw in (text_content or "") for kw in sold_out_keywords):
                        return True
            except Exception:
                pass

            # 策略2：enabled 属性
            enabled = await loop.run_in_executor(None, lambda: element.get_attribute("enabled"))
            if enabled == "false":
                return True

            # 策略3：clickable 属性
            clickable = await loop.run_in_executor(None, lambda: element.get_attribute("clickable"))
            if clickable == "false":
                return True

            return False
        except Exception:
            # 无法判断时保守返回 False（尝试点击）
            return False

    @staticmethod
    def _parse_price(price_text: str) -> Optional[int]:
        """
        从价格文本中提取整数金额（元）。
        支持格式：'¥380'  '380元'  '380.00'  'VIP¥1280'
        返回 None 表示解析失败。
        """
        import re
        if not price_text:
            return None
        # 提取数字（含小数点）
        match = re.search(r"(\d+(?:\.\d+)?)", price_text.replace(",", ""))
        if match:
            return int(float(match.group(1)))
        return None

    async def _dismiss_popup(self) -> bool:
        """
        尝试关闭可能出现的弹窗（广告、权限请求、登录提示等）。
        在关键步骤前调用，避免弹窗遮挡目标元素。
        返回 True 表示确实关闭了弹窗。
        """
        close_xpaths = [
            '//*[@resource-id="cn.damai:id/dialog_close"]',
            '//*[@resource-id="cn.damai:id/btn_cancel"]',
            '//*[contains(@text,"关闭") and @clickable="true"]',
            '//*[contains(@text,"取消") and @clickable="true"]',
            '//*[contains(@text,"我知道了") and @clickable="true"]',
            '//*[@content-desc="关闭"]',
        ]
        for xpath in close_xpaths:
            el = await self._find_element(AppiumBy.XPATH, xpath)
            if el:
                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, el.click)
                    logger.debug(f"[Android] 关闭弹窗: {xpath}")
                    await asyncio.sleep(0.3)
                    return True
                except Exception:
                    continue
        return False

    async def _scroll_to_element(self, element) -> bool:
        """
        将指定元素滚动到屏幕可见区域（用于票档列表较长时）。
        使用 Appium 的 mobile: scrollGesture。
        """
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.driver.execute_script(
                    "mobile: scrollGesture",
                    {
                        "elementId": element.id,
                        "direction": "down",
                        "percent":   0.5,
                    }
                )
            )
            return True
        except Exception as e:
            logger.debug(f"[Android] 滚动到元素失败: {e}")
            return False

    async def take_screenshot(self, filename: str) -> bool:
        """
        截图保存到本地，用于调试和错误记录。
        filename 应包含完整路径，如 'logs/screenshots/error_001.png'。
        """
        if self.driver is None:
            logger.error("设备未连接")
            return False
        if not self._check_driver():
            return False
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: self.driver.save_screenshot(filename))
            logger.info(f"[Android] 截图已保存: {filename}")
            return True
        except Exception as e:
            logger.warning(f"[Android] 截图失败 {self.device_id}: {e}")
            return False

    async def get_current_page_source(self) -> str:
        """
        获取当前页面 XML 源码，用于调试元素定位问题。
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
            logger.warning(f"[Android] 获取页面源码失败: {e}")
            return ""

    async def press_back(self):
        """模拟按下 Android 返回键。"""
        if self.driver is None:
            logger.error("设备未连接")
            return
        if self._check_driver():
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, lambda: self.driver.press_keycode(4))  # KEYCODE_BACK = 4
            except Exception as e:
                logger.debug(f"[Android] 按返回键失败: {e}")

    def __repr__(self) -> str:
        status = "已连接" if self._connected else "未连接"
        return f"<AndroidDriver device={self.device_id} status={status}>"


# ══════════════════════════════════════════════════════════════════
# 模块自测（直接运行此文件时执行）
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) < 2:
        print("用法: python android_driver.py <device_id> [appium_server]")
        print("示例: python android_driver.py emulator-5554 http://127.0.0.1:4723")
        sys.exit(1)

    _device_id     = sys.argv[1]
    _appium_server = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:4723"

    drv = AndroidDriver(_device_id, _appium_server)

    print(f"\n{'='*50}")
    print(f"  Android Driver 自测")
    print(f"  设备: {_device_id}")
    print(f"  Appium: {_appium_server}")
    print(f"{'='*50}\n")

    async def run_test():
        # 1. 获取设备信息（不需要 Appium）
        print("[1/4] 获取设备信息（ADB）...")
        info = await drv.get_device_info()
        for k, v in info.items():
            print(f"      {k:15s}: {v}")

        # 2. 连接 Appium
        print("\n[2/4] 连接 Appium...")
        if not await drv.connect():
            print("      ❌ 连接失败，请确认 Appium 服务已启动且设备已授权")
            sys.exit(1)
        print(f"      ✅ 连接成功 → {drv}")

        # 3. 启动大麦 APP
        print("\n[3/4] 启动大麦 APP...")
        ok = await drv.start_app()
        print(f"      {'✅ 启动成功' if ok else '❌ 启动失败'}")

        # 4. 截图验证
        print("\n[4/4] 截图验证...")
        ok = await drv.take_screenshot("test_screenshot.png")
        print(f"      {'✅ 截图已保存: test_screenshot.png' if ok else '❌ 截图失败'}")

        # 清理
        await drv.disconnect()
        print("\n✅ 自测完成，设备已断开\n")

    asyncio.run(run_test())

