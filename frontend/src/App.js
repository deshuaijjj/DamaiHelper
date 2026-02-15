import React, { useState, useEffect } from 'react';
import { Layout, Card, Button, List, Tag, Space, message, Modal, Form, Input, DatePicker, Select, InputNumber } from 'antd';
import { MobileOutlined, AppleOutlined, AndroidOutlined, ReloadOutlined, PlayCircleOutlined, StopOutlined, DeleteOutlined } from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import './App.css';

const { Header, Content } = Layout;
const { Option } = Select;

const API_BASE = 'http://127.0.0.1:8000';

function App() {
  const [devices, setDevices] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [taskModalVisible, setTaskModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 扫描设备
  const scanDevices = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/api/devices/scan`);
      const { android, ios } = response.data;
      
      // 自动连接扫描到的设备
      for (const deviceId of android) {
        await axios.post(`${API_BASE}/api/devices/connect?device_id=${deviceId}&platform=android`);
      }
      for (const deviceId of ios) {
        await axios.post(`${API_BASE}/api/devices/connect?device_id=${deviceId}&platform=ios`);
      }
      
      // 获取已连接设备
      await fetchDevices();
      message.success('设备扫描完成');
    } catch (error) {
      message.error('扫描设备失败: ' + error.message);
    }
    setLoading(false);
  };

  // 获取已连接设备
  const fetchDevices = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/devices`);
      setDevices(response.data.devices);
    } catch (error) {
      console.error('获取设备失败:', error);
    }
  };

  // 获取任务列表
  const fetchTasks = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/tasks`);
      setTasks(response.data.tasks);
    } catch (error) {
      console.error('获取任务失败:', error);
    }
  };

  // 创建任务
  const createTask = async (values) => {
    try {
      const taskData = {
        task_id: `task_${Date.now()}`,
        event_name: values.event_name,
        event_url: values.event_url,
        start_time: values.start_time.toISOString(),
        target_price: values.target_price,
        quantity: values.quantity,
        device_ids: values.device_ids,
        status: 'pending'
      };
      
      await axios.post(`${API_BASE}/api/tasks`, taskData);
      message.success('任务创建成功');
      setTaskModalVisible(false);
      form.resetFields();
      fetchTasks();
    } catch (error) {
      message.error('创建任务失败: ' + error.message);
    }
  };

  // 启动任务
  const startTask = async (taskId) => {
    try {
      await axios.post(`${API_BASE}/api/tasks/${taskId}/start`);
      message.success('任务已启动');
      fetchTasks();
    } catch (error) {
      message.error('启动任务失败: ' + error.message);
    }
  };

  // 停止任务
  const stopTask = async (taskId) => {
    try {
      await axios.post(`${API_BASE}/api/tasks/${taskId}/stop`);
      message.success('任务已停止');
      fetchTasks();
    } catch (error) {
      message.error('停止任务失败: ' + error.message);
    }
  };

  // 删除任务
  const deleteTask = async (taskId) => {
    try {
      await axios.delete(`${API_BASE}/api/tasks/${taskId}`);
      message.success('任务已删除');
      fetchTasks();
    } catch (error) {
      message.error('删除任务失败: ' + error.message);
    }
  };

  // 测试Android设备
  const testAndroidDevice = async (deviceId) => {
    try {
      const response = await axios.post(`${API_BASE}/api/test/android?device_id=${deviceId}`);
      if (response.data.success) {
        message.success('设备测试成功，大麦APP已启动');
      } else {
        message.error('设备测试失败');
      }
    } catch (error) {
      message.error('测试失败: ' + error.message);
    }
  };

  useEffect(() => {
    fetchDevices();
    fetchTasks();
    
    // 定时刷新
    const interval = setInterval(() => {
      fetchDevices();
      fetchTasks();
    }, 3000);
    
    return () => clearInterval(interval);
  }, []);

  const getStatusTag = (status) => {
    const statusMap = {
      pending: { color: 'default', text: '等待中' },
      running: { color: 'processing', text: '运行中' },
      success: { color: 'success', text: '成功' },
      failed: { color: 'error', text: '失败' },
      stopped: { color: 'warning', text: '已停止' }
    };
    const config = statusMap[status] || statusMap.pending;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <h1>🎫 DamaiHelper - 大麦抢票助手</h1>
      </Header>
      
      <Content className="app-content">
        {/* 设备管理 */}
        <Card 
          title="📱 设备管理" 
          extra={
            <Button 
              icon={<ReloadOutlined />} 
              onClick={scanDevices}
              loading={loading}
            >
              扫描设备
            </Button>
          }
          style={{ marginBottom: 20 }}
        >
          {devices.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
              <MobileOutlined style={{ fontSize: 48, marginBottom: 16 }} />
              <p>未检测到设备，请连接手机到电脑</p>
              <Button type="primary" onClick={scanDevices}>开始扫描</Button>
            </div>
          ) : (
            <List
              dataSource={devices}
              renderItem={(device) => (
                <List.Item
                  actions={[
                    device.platform === 'android' && (
                      <Button 
                        size="small" 
                        onClick={() => testAndroidDevice(device.device_id)}
                      >
                        测试
                      </Button>
                    )
                  ]}
                >
                  <List.Item.Meta
                    avatar={
                      device.platform === 'ios' ? 
                        <AppleOutlined style={{ fontSize: 24 }} /> : 
                        <AndroidOutlined style={{ fontSize: 24 }} />
                    }
                    title={`${device.brand || device.name || 'Unknown'} ${device.model || ''}`}
                    description={
                      <Space>
                        <Tag color={device.platform === 'ios' ? 'blue' : 'green'}>
                          {device.platform === 'ios' ? 'iOS' : 'Android'} {device.version}
                        </Tag>
                        <Tag color="success">已连接</Tag>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Card>

        {/* 任务管理 */}
        <Card 
          title="🎯 抢票任务" 
          extra={
            <Button 
              type="primary" 
              onClick={() => setTaskModalVisible(true)}
              disabled={devices.length === 0}
            >
              创建任务
            </Button>
          }
        >
          {tasks.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
              <p>暂无任务，点击"创建任务"开始</p>
            </div>
          ) : (
            <List
              dataSource={tasks}
              renderItem={(task) => (
                <List.Item
                  actions={[
                    task.status === 'pending' && (
                      <Button 
                        type="primary" 
                        size="small" 
                        icon={<PlayCircleOutlined />}
                        onClick={() => startTask(task.task_id)}
                      >
                        启动
                      </Button>
                    ),
                    task.status === 'running' && (
                      <Button 
                        danger 
                        size="small" 
                        icon={<StopOutlined />}
                        onClick={() => stopTask(task.task_id)}
                      >
                        停止
                      </Button>
                    ),
                    <Button 
                      danger 
                      size="small" 
                      icon={<DeleteOutlined />}
                      onClick={() => deleteTask(task.task_id)}
                    >
                      删除
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    title={task.event_name}
                    description={
                      <Space direction="vertical">
                        <span>开票时间: {dayjs(task.start_time).format('YYYY-MM-DD HH:mm:ss')}</span>
                        {getStatusTag(task.status)}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Card>

        {/* 创建任务弹窗 */}
        <Modal
          title="创建抢票任务"
          open={taskModalVisible}
          onCancel={() => setTaskModalVisible(false)}
          footer={null}
          width={600}
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={createTask}
          >
            <Form.Item
              label="演出名称"
              name="event_name"
              rules={[{ required: true, message: '请输入演出名称' }]}
            >
              <Input placeholder="例如：周杰伦演唱会" />
            </Form.Item>

            <Form.Item
              label="演出链接"
              name="event_url"
              rules={[{ required: true, message: '请输入大麦链接' }]}
            >
              <Input placeholder="粘贴大麦详情页链接" />
            </Form.Item>

            <Form.Item
              label="开票时间"
              name="start_time"
              rules={[{ required: true, message: '请选择开票时间' }]}
            >
              <DatePicker 
                showTime 
                format="YYYY-MM-DD HH:mm:ss"
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item
              label="目标票价"
              name="target_price"
            >
              <InputNumber 
                placeholder="例如：1280" 
                style={{ width: '100%' }}
                prefix="¥"
              />
            </Form.Item>

            <Form.Item
              label="购买数量"
              name="quantity"
              initialValue={1}
              rules={[{ required: true }]}
            >
              <InputNumber min={1} max={6} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item
              label="选择设备"
              name="device_ids"
              rules={[{ required: true, message: '请选择至少一个设备' }]}
            >
              <Select mode="multiple" placeholder="选择要使用的设备">
                {devices.map(device => (
                  <Option key={device.device_id} value={device.device_id}>
                    {device.brand || device.name} {device.model} ({device.platform})
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item>
              <Space>
                <Button type="primary" htmlType="submit">
                  创建任务
                </Button>
                <Button onClick={() => setTaskModalVisible(false)}>
                  取消
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>
      </Content>
    </Layout>
  );
}

export default App;

