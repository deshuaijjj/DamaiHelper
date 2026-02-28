import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ConfigProvider, Layout, Card, Button, List, Space, message, Modal, Form, Input, DatePicker, Select, Badge, Popconfirm, Typography } from 'antd';
// 【BUG-J3修复】删除未使用的 PlayCircleOutlined 导入
import { AppleOutlined, AndroidOutlined, ReloadOutlined, StopOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import './App.css';

const { Sider, Content } = Layout;
const { Option } = Select;
const { Link } = Typography;

// 【代码质量15】使用环境变量配置 API 地址，便于部署
const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:8000';
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://127.0.0.1:8000/ws';

// 【代码质量13】将 StatusIndicator 组件移到 App 函数外部，避免每次渲染重新定义
const StatusIndicator = ({ status }) => {
  const statusConfig = {
    success: { color: '#34C759', text: '成功' },
    failed: { color: '#FF3B30', text: '失败' },
    running: { color: '#007AFF', text: '运行中' },
    cancelled: { color: '#FF9500', text: '已取消' },
    pending: { color: '#8E8E93', text: '等待中' },
    waiting: { color: '#8E8E93', text: '等待中' }
  };
  
  const config = statusConfig[status] || statusConfig.pending;
  
  return (
    <div className="status-indicator">
      <span className="status-dot" style={{ backgroundColor: config.color }}></span>
      <span className="status-text">{config.text}</span>
    </div>
  );
};

function App() {
  const [devices, setDevices] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [taskModalVisible, setTaskModalVisible] = useState(false);
  const [selectedMenu, setSelectedMenu] = useState('devices');
  const [wsConnected, setWsConnected] = useState(false);
  const [form] = Form.useForm();
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);

  // 【BUG修复7】在组件顶层添加 ref 跟踪卸载状态
  const isUnmountedRef = useRef(false);

  // WebSocket 连接
  // 【次要问题7修复】使用 useCallback 包装，避免不必要的重新创建
  const connectWebSocket = useCallback(() => {
    // 【BUG-J1修复】关闭旧连接，防止重复连接
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close();
    }
    
    try {
      const ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        console.log('WebSocket 已连接');
        setWsConnected(true);
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          // 【BUG修复5】重命名变量避免与 antd 的 message 对象冲突
          const wsMessage = JSON.parse(event.data);
          if (wsMessage.type === 'task_update' && wsMessage.data) {
            // 局部更新任务状态
            setTasks(prevTasks => 
              prevTasks.map(task => 
                task.task_id === wsMessage.data.task_id ? { ...task, ...wsMessage.data } : task
              )
            );
          }
          // 【BUG修复6】处理设备断开连接的消息
          else if (wsMessage.type === 'device_disconnected') {
            fetchDevices();
          }
        } catch (error) {
          console.error('解析 WebSocket 消息失败:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket 已断开');
        setWsConnected(false);
        // 【BUG修复7】使用 ref 检查组件是否已卸载，避免内存泄漏
        if (isUnmountedRef.current) return;
        // 3秒后自动重连
        reconnectTimerRef.current = setTimeout(() => {
          console.log('尝试重新连接 WebSocket...');
          connectWebSocket();
        }, 3000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket 连接失败:', error);
      setWsConnected(false);
    }
  }, []); // 【次要问题7修复】空依赖数组，函数只创建一次

  // 扫描并连接设备
  const scanDevices = async () => {
    setLoading(true);
    try {
      // 第一步：扫描设备
      const scanResponse = await axios.get(`${API_BASE}/api/devices/scan`);
      const { android = [], ios = [] } = scanResponse.data;
      
      // 第二步：连接所有扫描到的设备
      const connectPromises = [];
      
      for (const deviceId of android) {
        connectPromises.push(
          axios.post(`${API_BASE}/api/devices/connect`, {
            device_id: deviceId,
            platform: 'android',
            bundle_id: null
          }).catch(err => console.error(`连接 Android 设备 ${deviceId} 失败:`, err))
        );
      }
      
      for (const deviceId of ios) {
        connectPromises.push(
          axios.post(`${API_BASE}/api/devices/connect`, {
            device_id: deviceId,
            platform: 'ios',
            bundle_id: 'cn.damai'
          }).catch(err => console.error(`连接 iOS 设备 ${deviceId} 失败:`, err))
        );
      }
      
      await Promise.all(connectPromises);
      
      // 第三步：获取已连接设备列表
      await fetchDevices();
      message.success(`设备扫描完成，发现 ${android.length + ios.length} 台设备`);
    } catch (error) {
      message.error('扫描设备失败: ' + error.message);
    } finally {
      // 【代码质量14】将 setLoading(false) 放入 finally 块，确保一定执行
      setLoading(false);
    }
  };

  // 获取已连接设备
  const fetchDevices = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/devices`);
      setDevices(response.data.devices || []);
    } catch (error) {
      console.error('获取设备失败:', error);
    }
  };

  // 断开设备
  const disconnectDevice = async (deviceId, platform) => {
    try {
      // 【BUG修复10】删除后端不接受的 platform 参数
      await axios.post(`${API_BASE}/api/devices/disconnect?device_id=${deviceId}`);
      message.success('设备已断开');
      await fetchDevices();
    } catch (error) {
      message.error('断开设备失败: ' + error.message);
    }
  };

  // 获取任务列表
  const fetchTasks = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/tasks/list`);
      if (response.data.success) {
        setTasks(response.data.tasks || []);
      }
    } catch (error) {
      console.error('获取任务失败:', error);
    }
  };

  // 创建任务
  const createTask = async (values) => {
    try {
      const taskData = {
        event_url: values.event_url,
        device_ids: values.device_ids,
        // 【BUG修复11】添加空值保护
        start_time: values.start_time ? values.start_time.toISOString() : null,
        platform: values.platform
      };
      
      const response = await axios.post(`${API_BASE}/api/tasks/create`, taskData);
      if (response.data.success) {
        message.success('任务已创建并开始调度');
        setTaskModalVisible(false);
        form.resetFields();
        await fetchTasks();
      }
    } catch (error) {
      message.error('创建任务失败: ' + error.message);
    }
  };

  // 停止任务
  const stopTask = async (taskId) => {
    try {
      const response = await axios.post(`${API_BASE}/api/tasks/stop?task_id=${taskId}`);
      if (response.data.success) {
        message.success('任务已停止');
        await fetchTasks();
      }
    } catch (error) {
      message.error('停止任务失败: ' + error.message);
    }
  };

  // 删除任务
  const deleteTask = async (taskId) => {
    try {
      const response = await axios.post(`${API_BASE}/api/tasks/remove?task_id=${taskId}`);
      if (response.data.success) {
        message.success('任务已删除');
        await fetchTasks();
      }
    } catch (error) {
      message.error('删除任务失败: ' + error.message);
    }
  };

  // 组件挂载时初始化
  useEffect(() => {
    fetchDevices();
    fetchTasks();
    connectWebSocket();

    return () => {
      // 【BUG修复7】设置卸载标志，阻止所有后续重连
      isUnmountedRef.current = true;
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, []);

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#007AFF',
          borderRadius: 8,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif',
        },
      }}
    >
      <Layout className="app-layout">
        {/* 左侧 Sidebar */}
        <Sider width={220} className="app-sidebar">
          <div className="sidebar-header">
            <h1 className="app-title">DamaiHelper</h1>
          </div>
          
          <div className="sidebar-menu">
            <div 
              className={`menu-item ${selectedMenu === 'devices' ? 'active' : ''}`}
              onClick={() => setSelectedMenu('devices')}
            >
              <span className="menu-icon">📱</span>
              <span className="menu-text">设备管理</span>
              <Badge count={devices.length} className="menu-badge" />
            </div>
            
            <div 
              className={`menu-item ${selectedMenu === 'tasks' ? 'active' : ''}`}
              onClick={() => setSelectedMenu('tasks')}
            >
              <span className="menu-icon">🎯</span>
              <span className="menu-text">抢票任务</span>
              <Badge count={tasks.length} className="menu-badge" />
            </div>
          </div>

          {/* WebSocket 连接状态 */}
          <div className="ws-status">
            <span className={`ws-dot ${wsConnected ? 'connected' : 'disconnected'}`}></span>
            <span className="ws-text">{wsConnected ? '已连接' : '未连接'}</span>
          </div>
        </Sider>

        {/* 右侧主内容区 */}
        <Content className="app-content">
          {/* 设备管理 */}
          {selectedMenu === 'devices' && (
            <div className="content-section">
              <div className="section-header">
                <h2 className="section-title">设备管理</h2>
                <Button 
                  type="primary"
                  icon={<ReloadOutlined />} 
                  onClick={scanDevices}
                  loading={loading}
                  className="action-button"
                >
                  扫描设备
                </Button>
              </div>

              <Card className="content-card">
                {devices.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-icon">📱</div>
                    <p className="empty-text">未检测到设备</p>
                    <p className="empty-hint">请连接手机到电脑并点击扫描</p>
                    <Button type="primary" onClick={scanDevices} loading={loading}>
                      开始扫描
                    </Button>
                  </div>
                ) : (
                  <List
                    dataSource={devices}
                    renderItem={(device) => (
                      <List.Item className="device-item">
                        <div className="device-info">
                          <div className="device-icon">
                            {device.platform === 'ios' ? 
                              <AppleOutlined style={{ fontSize: 24, color: '#000' }} /> : 
                              <AndroidOutlined style={{ fontSize: 24, color: '#3DDC84' }} />
                            }
                          </div>
                          <div className="device-details">
                            <div className="device-name">
                              {device.brand || device.name || 'Unknown Device'} {device.model || ''}
                            </div>
                            <div className="device-meta">
                              <span className="device-platform">
                                {device.platform === 'ios' ? 'iOS' : 'Android'} {device.version}
                              </span>
                              <span className="device-separator">•</span>
                              <span className="device-id">{device.device_id}</span>
                            </div>
                          </div>
                        </div>
                        <Button 
                          size="small" 
                          danger
                          onClick={() => disconnectDevice(device.device_id, device.platform)}
                        >
                          断开
                        </Button>
                      </List.Item>
                    )}
                  />
                )}
              </Card>
            </div>
          )}

          {/* 任务管理 */}
          {selectedMenu === 'tasks' && (
            <div className="content-section">
              <div className="section-header">
                <h2 className="section-title">抢票任务</h2>
                <Button 
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setTaskModalVisible(true)}
                  disabled={devices.length === 0}
                  className="action-button"
                >
                  创建任务
                </Button>
              </div>

              <Card className="content-card">
                {tasks.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-icon">🎯</div>
                    <p className="empty-text">暂无任务</p>
                    <p className="empty-hint">点击"创建任务"开始抢票</p>
                  </div>
                ) : (
                  <List
                    dataSource={tasks}
                    renderItem={(task) => (
                      <List.Item className="task-item">
                        <div className="task-info">
                          <div className="task-header">
                            <div className="task-title">任务 {task.task_id}</div>
                            <StatusIndicator status={task.status} />
                          </div>
                          <div className="task-details">
                            <div className="task-detail-item">
                              <span className="detail-label">开始时间:</span>
                              <span className="detail-value">
                                {/* 【BUG修复8】处理 start_time 为 null 的情况 */}
                                {task.start_time
                                  ? dayjs(task.start_time).format('YYYY-MM-DD HH:mm:ss')
                                  : '立即执行'}
                              </span>
                            </div>
                            {/* 【BUG修复8】展示演出链接 */}
                            <div className="task-detail-item">
                              <span className="detail-label">演出链接:</span>
                              <Link href={task.event_url} target="_blank" className="detail-value">
                                {task.event_url}
                              </Link>
                            </div>
                            <div className="task-detail-item">
                              <span className="detail-label">设备数量:</span>
                              <span className="detail-value">{task.device_ids?.length || 0} 台</span>
                            </div>
                            <div className="task-detail-item">
                              <span className="detail-label">平台:</span>
                              <span className="detail-value">
                                {task.platform === 'ios' ? 'iOS' : 'Android'}
                              </span>
                            </div>
                          </div>
                        </div>
                        <Space className="task-actions">
                          {task.status === 'running' && (
                            <Button 
                              danger
                              size="small" 
                              icon={<StopOutlined />}
                              onClick={() => stopTask(task.task_id)}
                            >
                              停止
                            </Button>
                          )}
                          {/* 【BUG修复7】添加删除任务的二次确认 */}
                          <Popconfirm
                            title="确认删除该任务？"
                            onConfirm={() => deleteTask(task.task_id)}
                            okText="确认"
                            cancelText="取消"
                          >
                            <Button 
                              danger
                              size="small" 
                              icon={<DeleteOutlined />}
                            >
                              删除
                            </Button>
                          </Popconfirm>
                        </Space>
                      </List.Item>
                    )}
                  />
                )}
              </Card>
            </div>
          )}
        </Content>

        {/* 创建任务弹窗 */}
        <Modal
          title="创建抢票任务"
          open={taskModalVisible}
          onCancel={() => {
            setTaskModalVisible(false);
            form.resetFields();
          }}
          footer={null}
          width={560}
          className="task-modal"
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={createTask}
          >
            <Form.Item
              label="演出链接"
              name="event_url"
              rules={[{ required: true, message: '请输入大麦详情页链接' }]}
            >
              <Input placeholder="粘贴大麦详情页链接" />
            </Form.Item>

            <Form.Item
              label="开票时间"
              name="start_time"
              // 【BUG-J2修复】去掉 required，支持立即执行
            >
              <DatePicker 
                showTime 
                format="YYYY-MM-DD HH:mm:ss"
                style={{ width: '100%' }}
                placeholder="选择开票时间（不填则立即执行）"
              />
            </Form.Item>

            <Form.Item
              label="平台"
              name="platform"
              rules={[{ required: true, message: '请选择平台' }]}
              initialValue="android"
            >
              <Select placeholder="选择平台">
                <Option value="android">Android</Option>
                <Option value="ios">iOS</Option>
              </Select>
            </Form.Item>

            <Form.Item
              label="选择设备"
              name="device_ids"
              rules={[{ required: true, message: '请选择至少一个设备' }]}
            >
              <Select mode="multiple" placeholder="选择要使用的设备">
                {devices.map(device => (
                  <Option key={device.device_id} value={device.device_id}>
                    {device.platform === 'ios' ? '🍎' : '🤖'} {device.brand || device.name} {device.model}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item>
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button onClick={() => {
                  setTaskModalVisible(false);
                  form.resetFields();
                }}>
                  取消
                </Button>
                <Button type="primary" htmlType="submit">
                  创建任务
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
