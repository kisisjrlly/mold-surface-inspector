"""
模具检测设备 - Modbus 仿真服务器
支持双探头系统：1#探头(左->中) 和 2#探头(右->中)

基于 simulation-of-device.html 的硬件仿真逻辑
包含双探头测量数据仿真（千分表读数）
"""

import time
import threading
import logging
import math
import random
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext
try:
    from pymodbus.datastore import ModbusSlaveContext
except ImportError:
    from pymodbus.datastore import ModbusDeviceContext as ModbusSlaveContext

# 配置日志
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)


class DualProbeSimulator(threading.Thread):
    """
    双探头检测设备模拟器
    
    机械结构（根据实际曲面尺寸 1410×796×600mm）：
    - 1#探头 (绿色): 安装在上导轨，从左侧(-700mm)向中心(100mm)移动
    - 2#探头 (蓝色): 安装在下导轨，从右侧(700mm)向中心(-100mm)移动
    - 旋转轴: 带动两个探头同时旋转，范围 0-170°
    - 重叠区域: -100mm 到 100mm，两个探头都会扫描这个区域
    
    传感器数据仿真：
    - 基于半圆柱模具理论模型生成测量数据
    - 添加高斯噪声模拟真实测量误差
    """
    
    # 机械参数（单位：0.01mm）
    SCALE = 100.0  # 位置精度 0.01mm，内部存储为整数
    PROBE_SCALE = 100.0  # 探头精度 0.01mm
    
    # 1#探头行程 (从左向右) - 根据实际曲面尺寸调整
    X1_HOME = -700.0  # mm，原点位置（左侧）
    X1_MIN = -700.0   # mm
    X1_MAX = 100.0    # mm，最大到中心略过
    
    # 2#探头行程 (从右向左)
    X2_HOME = 700.0   # mm，原点位置（右侧）
    X2_MIN = -100.0   # mm，最小到中心略过
    X2_MAX = 700.0    # mm
    
    # 旋转轴 (双向旋转)
    ROT_HOME = 0.0      # 度
    ROT_MIN = -180.0    # 度
    ROT_MAX = 180.0     # 度
    
    # 速度参数 (每100ms移动量)
    X_SPEED_DEFAULT = 10.0    # mm/100ms (100mm/s，加快仿真速度)
    ROT_SPEED_DEFAULT = 5.0   # 度/100ms (50度/s，加快仿真速度)
    
    # 模具参数 - 根据实际曲面尺寸
    MOLD_RADIUS = 400.0  # mm，模具半径（约为Y方向尺寸的一半）
    
    # 测量噪声参数
    MEASUREMENT_NOISE_STD = 0.03  # mm，测量噪声标准差
    
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.slave_id = 1
        self.running = True
        
        # 初始化位置到原点
        self._set_position(1, self.X1_HOME)
        self._set_position(2, self.X2_HOME)
        self._set_position(3, self.ROT_HOME)
        
        # 初始化探头测量值
        self._set_probe_measurement(1, 0.0)
        self._set_probe_measurement(2, 0.0)
        
        # 设置初始化完成标志
        store = self.context[self.slave_id]
        store.setValues(1, 900, [True])   # 1#X轴初始化完成
        store.setValues(1, 901, [True])   # 2#X轴初始化完成
        store.setValues(1, 902, [True])   # 旋转轴初始化完成
        store.setValues(1, 701, [True])   # 系统初始化完成

    def run(self):
        log.info("Dual-Probe Machine Simulator Started")
        log.info(f"1# Probe: {self.X1_MIN}mm -> {self.X1_MAX}mm (Left to Center)")
        log.info(f"2# Probe: {self.X2_MAX}mm -> {self.X2_MIN}mm (Right to Center)")
        log.info(f"Rotation: {self.ROT_MIN}° -> {self.ROT_MAX}°")
        log.info(f"Mold Radius: {self.MOLD_RADIUS}mm")
        
        while self.running:
            self._check_system_init()  # 检查整机初始化
            self._update_axis(1)  # 1#X轴
            self._update_axis(2)  # 2#X轴
            self._update_axis(3)  # 旋转轴
            self._update_probe_measurements()  # 更新探头测量数据
            time.sleep(0.1)  # 100ms 循环
    
    def _check_system_init(self):
        """检查整机初始化信号"""
        store = self.context[self.slave_id]
        is_system_init = store.getValues(1, 104, count=1)[0]
        
        if is_system_init:
            # 触发所有轴的初始化
            store.setValues(1, 1002, [True])  # 1#X轴初始化
            store.setValues(1, 1102, [True])  # 2#X轴初始化
            store.setValues(1, 1202, [True])  # 旋转轴初始化
            
            # 设置初始化中标志
            store.setValues(1, 700, [True])   # 系统初始化中
            store.setValues(1, 1003, [True])  # 1#X轴初始化中
            store.setValues(1, 1103, [True])  # 2#X轴初始化中
            store.setValues(1, 1203, [True])  # 旋转轴初始化中
            
            # 复位整机初始化信号
            store.setValues(1, 104, [False])
            
            log.info("整机初始化启动")
    
    def _update_probe_measurements(self):
        """
        更新双探头测量数据（仿真千分表读数）
        
        基于当前位置和旋转角度，计算理论半径值并添加测量噪声
        """
        store = self.context[self.slave_id]
        
        # 读取当前位置
        x1_raw = self._decode_dint(store.getValues(3, 2000, count=2))
        x2_raw = self._decode_dint(store.getValues(3, 2002, count=2))
        rot_raw = self._decode_dint(store.getValues(3, 2004, count=2))
        
        x1_mm = x1_raw / self.SCALE
        x2_mm = x2_raw / self.SCALE
        angle_deg = rot_raw / self.SCALE
        
        # 计算仿真测量值
        # 理论值：半圆柱模具，半径为 MOLD_RADIUS
        # 测量值 = 理论值 + 高斯噪声
        
        # 1#探头测量值（测量上半圆柱）
        probe1_theoretical = self.MOLD_RADIUS
        probe1_noise = random.gauss(0, self.MEASUREMENT_NOISE_STD)
        probe1_measured = probe1_theoretical + probe1_noise
        self._set_probe_measurement(1, probe1_measured)
        
        # 2#探头测量值（测量下半圆柱，对称结构，理论值相同）
        probe2_theoretical = self.MOLD_RADIUS
        probe2_noise = random.gauss(0, self.MEASUREMENT_NOISE_STD)
        probe2_measured = probe2_theoretical + probe2_noise
        self._set_probe_measurement(2, probe2_measured)
    
    def _set_probe_measurement(self, probe_id, value_mm):
        """
        设置探头测量值（单位：mm，精度：0.01mm）
        
        Args:
            probe_id: 1 或 2
            value_mm: 测量值（mm）
        """
        addr = 110 if probe_id == 1 else 112
        store = self.context[self.slave_id]
        
        # 转换为整数存储（0.01mm 精度）
        value_int = int(value_mm * self.PROBE_SCALE)
        store.setValues(3, addr, self._encode_dint(value_int))

    def _update_axis(self, axis_id):
        """更新单个轴的运动"""
        # 地址映射
        addr_map = {
            1: {'current': 2000, 'target': 41212, 'action': 1010, 'moving': 720, 
                'speed': 41190, 'jog_speed': 41188, 'jog_fwd': 1000, 'jog_bwd': 1001, 'init': 1002,
                'min': self.X1_MIN, 'max': self.X1_MAX, 'home': self.X1_HOME, 'default_speed': self.X_SPEED_DEFAULT},
            2: {'current': 2002, 'target': 41312, 'action': 1110, 'moving': 721,
                'speed': 41290, 'jog_speed': 41288, 'jog_fwd': 1100, 'jog_bwd': 1101, 'init': 1102,
                'min': self.X2_MIN, 'max': self.X2_MAX, 'home': self.X2_HOME, 'default_speed': self.X_SPEED_DEFAULT},
            3: {'current': 2004, 'target': 41412, 'action': 1210, 'moving': 722,
                'speed': 41390, 'jog_speed': None, 'jog_fwd': 1200, 'jog_bwd': 1201, 'init': 1202,
                'min': self.ROT_MIN, 'max': self.ROT_MAX, 'home': self.ROT_HOME, 'default_speed': self.ROT_SPEED_DEFAULT}
        }
        
        addr = addr_map[axis_id]
        store = self.context[self.slave_id]
        
        # 读取当前位置
        current_val = self._decode_dint(store.getValues(3, addr['current'], count=2))
        current = current_val / self.SCALE
        
        # 检查初始化信号
        is_init = store.getValues(1, addr['init'], count=1)[0]
        if is_init:
            # 执行回原点
            target = addr['home']
            diff = target - current
            speed = addr['default_speed']
            
            # 初始化状态标志地址映射
            init_status_map = {
                1: {'ing': 1003, 'done': 900},  # 1#X轴
                2: {'ing': 1103, 'done': 901},  # 2#X轴
                3: {'ing': 1203, 'done': 902}   # 旋转轴
            }
            
            if abs(diff) <= speed * 0.1:  # 到达原点
                self._set_position(axis_id, target)
                store.setValues(1, addr['init'], [False])  # 复位初始化信号
                store.setValues(1, addr['moving'], [False])
                store.setValues(1, init_status_map[axis_id]['ing'], [False])  # 初始化中标志清除
                store.setValues(1, init_status_map[axis_id]['done'], [True])  # 初始化完成标志置位
                log.info(f"轴{axis_id}初始化完成，位置: {target}")
                
                # 检查所有轴是否都初始化完成
                all_done = all(store.getValues(1, init_status_map[i]['done'], count=1)[0] for i in [1, 2, 3])
                if all_done:
                    store.setValues(1, 700, [False])  # 系统初始化中标志清除
                    store.setValues(1, 701, [True])   # 系统初始化完成
                    log.info("整机初始化完成")
            else:
                step = speed if diff > 0 else -speed
                new_val = current + step
                self._set_position(axis_id, new_val)
                store.setValues(1, addr['moving'], [True])
                store.setValues(1, init_status_map[axis_id]['ing'], [True])  # 初始化中
            return
        
        # 检查点动信号
        is_jog_fwd = store.getValues(1, addr['jog_fwd'], count=1)[0]
        is_jog_bwd = store.getValues(1, addr['jog_bwd'], count=1)[0]
        
        if is_jog_fwd or is_jog_bwd:
            # 读取点动速度
            if addr['jog_speed']:
                # X轴：从寄存器读取点动速度（单位：mm）
                jog_speed_regs = store.getValues(3, addr['jog_speed'], count=2)
                jog_speed_raw = self._decode_dint(jog_speed_regs)
                jog_speed = jog_speed_raw if jog_speed_raw > 0 else addr['default_speed']
            else:
                # 旋转轴：使用默认速度（单位：度），不乘以SCALE
                jog_speed = addr['default_speed']
            
            # 点动运动（每100ms移动jog_speed单位距离）
            step = jog_speed if is_jog_fwd else -jog_speed
            new_val = current + step
            
            # 限位保护
            new_val = max(addr['min'], min(addr['max'], new_val))
            
            self._set_position(axis_id, new_val)
            store.setValues(1, addr['moving'], [True])
            return
        
        # 检查动作信号
        is_action = store.getValues(1, addr['action'], count=1)[0]
        
        if is_action:
            # 读取目标位置和当前位置
            target_val = self._decode_dint(store.getValues(3, addr['target'], count=2))
            current_val = self._decode_dint(store.getValues(3, addr['current'], count=2))
            
            # 转换为实际值
            if axis_id == 3:  # 旋转轴，单位是 0.01 度
                target = target_val / self.SCALE
                current = current_val / self.SCALE
            else:  # X轴，单位是 0.01mm
                target = target_val / self.SCALE
                current = current_val / self.SCALE
            
            # 限位保护
            target = max(addr['min'], min(addr['max'], target))
            
            # 读取速度设置（如果有）
            speed_regs = store.getValues(3, addr['speed'], count=2)
            speed_raw = self._decode_dint(speed_regs)
            speed = (speed_raw / self.SCALE) if speed_raw > 0 else addr['default_speed']
            
            # 计算移动
            diff = target - current
            
            if abs(diff) <= speed * 0.1:  # 考虑精度，到达目标
                new_val = target
                # 到达目标后复位动作信号
                store.setValues(1, addr['action'], [False])
                store.setValues(1, addr['moving'], [False])
            else:
                # 移动一步
                step = speed if diff > 0 else -speed
                new_val = current + step
                store.setValues(1, addr['moving'], [True])
            
            # 更新当前位置
            self._set_position(axis_id, new_val)
        else:
            # 确保 Moving 信号为 False
            store.setValues(1, addr['moving'], [False])

    def _set_position(self, axis_id, value_real):
        """设置轴位置 (输入为实际值 mm 或 度)"""
        addr_current = {1: 2000, 2: 2002, 3: 2004}[axis_id]
        store = self.context[self.slave_id]
        
        # 转换为整数存储（0.01 精度）
        value_int = int(value_real * self.SCALE)
        store.setValues(3, addr_current, self._encode_dint(value_int))

    def _decode_dint(self, registers):
        """解码 32位整数 (小端字序)"""
        r0, r1 = registers[0], registers[1]
        val = (r1 << 16) | r0
        if val >= 0x80000000:
            val -= 0x100000000
        return val

    def _encode_dint(self, value):
        """编码 32位整数 (小端字序)"""
        if value < 0:
            value += 0x100000000
        r0 = value & 0xFFFF
        r1 = (value >> 16) & 0xFFFF
        return [r0, r1]

    def stop(self):
        self.running = False


def run_server():
    """启动 Modbus TCP 服务器"""
    # 初始化数据块
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0] * 2000),   # 离散输入
        co=ModbusSequentialDataBlock(0, [0] * 2000),   # 线圈
        hr=ModbusSequentialDataBlock(0, [0] * 50000),  # 保持寄存器
        ir=ModbusSequentialDataBlock(0, [0] * 50000)   # 输入寄存器
    )
    context = ModbusServerContext(store, single=True)

    # 启动模拟逻辑线程
    sim_thread = DualProbeSimulator(context)
    sim_thread.start()

    # 启动 Modbus TCP 服务器
    log.info("Starting Modbus TCP Server on localhost:502...")
    try:
        StartTcpServer(context=context, address=("127.0.0.1", 502))
    except Exception as e:
        log.error(f"Server Error: {e}")
    finally:
        sim_thread.stop()


if __name__ == "__main__":
    run_server()
