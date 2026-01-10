"""
模具检测设备 - Modbus 仿真服务器
支持双探头系统：1#探头(左->中) 和 2#探头(右->中)

基于 simulation-of-device.html 的硬件仿真逻辑
"""

import time
import threading
import logging
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
    
    机械结构：
    - 1#探头 (绿色): 安装在上导轨，从左侧(-300mm)向中心(60mm)移动
    - 2#探头 (蓝色): 安装在下导轨，从右侧(300mm)向中心(-60mm)移动
    - 旋转轴: 带动两个探头同时旋转，范围 0-170°
    - 重叠区域: -60mm 到 60mm，两个探头都会扫描这个区域
    """
    
    # 机械参数（单位：0.01mm）
    SCALE = 100.0  # 精度 0.01mm，内部存储为整数
    
    # 1#探头行程 (从左向右)
    X1_HOME = -300.0  # mm，原点位置（左侧）
    X1_MIN = -300.0   # mm
    X1_MAX = 60.0     # mm，最大到中心略过
    
    # 2#探头行程 (从右向左)
    X2_HOME = 300.0   # mm，原点位置（右侧）
    X2_MIN = -60.0    # mm，最小到中心略过
    X2_MAX = 300.0    # mm
    
    # 旋转轴
    ROT_HOME = 0.0    # 度
    ROT_MIN = 0.0     # 度
    ROT_MAX = 170.0   # 度
    
    # 速度参数 (每100ms移动量)
    X_SPEED_DEFAULT = 500.0    # mm/100ms (50mm/s)
    ROT_SPEED_DEFAULT = 20.0  # 度/100ms (20度/s)
    
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.slave_id = 1
        self.running = True
        
        # 初始化位置到原点
        self._set_position(1, self.X1_HOME)
        self._set_position(2, self.X2_HOME)
        self._set_position(3, self.ROT_HOME)
        
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
        
        while self.running:
            self._update_axis(1)  # 1#X轴
            self._update_axis(2)  # 2#X轴
            self._update_axis(3)  # 旋转轴
            time.sleep(0.1)  # 100ms 循环

    def _update_axis(self, axis_id):
        """更新单个轴的运动"""
        # 地址映射
        addr_map = {
            1: {'current': 2000, 'target': 41212, 'action': 1010, 'moving': 720, 
                'speed': 41190, 'min': self.X1_MIN, 'max': self.X1_MAX, 'default_speed': self.X_SPEED_DEFAULT},
            2: {'current': 2002, 'target': 41312, 'action': 1110, 'moving': 721,
                'speed': 41290, 'min': self.X2_MIN, 'max': self.X2_MAX, 'default_speed': self.X_SPEED_DEFAULT},
            3: {'current': 2004, 'target': 41412, 'action': 1210, 'moving': 722,
                'speed': 41390, 'min': self.ROT_MIN, 'max': self.ROT_MAX, 'default_speed': self.ROT_SPEED_DEFAULT}
        }
        
        addr = addr_map[axis_id]
        store = self.context[self.slave_id]
        
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
