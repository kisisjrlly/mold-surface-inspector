import logging
import time
import struct
from pymodbus.client import ModbusTcpClient

# 配置日志
logger = logging.getLogger("PLCDriver")
# logging.basicConfig(level=logging.INFO) # 由主程序配置

class PLCDriver:
    """
    基于 Modbus TCP 的 PLC 通信驱动
    对应协议文档: PC-PLC通信协议.csv (Rev1.10)
    支持双 X 轴 (Top/Bottom) 和单旋转轴
    """
    def __init__(self, ip='127.0.0.1', port=502, slave_id=1):
        self.ip = ip
        self.port = port
        self.slave_id = slave_id
        self.client = ModbusTcpClient(ip, port=port)
        self.connected = False

    # ==============================
    # 1. 基础通信接口
    # ==============================
    
    def connect(self):
        """连接 PLC"""
        try:
            self.connected = self.client.connect()
            if self.connected:
                logger.info(f"PLC Connected: {self.ip}:{self.port}")
            else:
                logger.error(f"PLC Connection Failed: {self.ip}:{self.port}")
            return self.connected
        except Exception as e:
            logger.error(f"Connection Error: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self.client.close()
        self.connected = False
        logger.info("PLC Disconnected")

    def send_heartbeat(self, value: int):
        """发送视觉心跳信号 (地址 2200)"""
        self._write_register(2200, value)

    def read_heartbeat(self) -> int:
        """读取 PLC 反馈心跳 (地址 2202)"""
        return self._read_register(2202)

    # ==============================
    # 2. 状态查询接口 (Getters)
    # ==============================

    def get_all_positions(self):
        """
        获取所有轴当前坐标
        :return: dict {'x1': mm, 'x2': mm, 'rotation': deg}
        """
        # 批量读取可能不连续，这里分开读取保证稳定性
        # 1# X轴 (Top)
        raw_x1 = self._read_dint(2000)
        x1_mm = raw_x1 * 0.01 if raw_x1 is not None else 0.0

        # 2# X轴 (Bottom)
        raw_x2 = self._read_dint(2002)
        x2_mm = raw_x2 * 0.01 if raw_x2 is not None else 0.0

        # 旋转轴 (假设精度 0.01度，如果协议未标明，通常与线性轴一致或为 0.1)
        # 根据 CSV 空白备注，暂定 0.01 以防万一，如果是整数度数则后续调整
        raw_r = self._read_dint(2004)
        r_deg = raw_r * 0.01 if raw_r is not None else 0.0
        
        return {
            'x1': x1_mm,
            'x2': x2_mm,
            'rotation': r_deg
        }

    def get_machine_status(self):
        """
        获取设备运行状态
        :return: dict 包含各轴运动状态和急停状态
        """
        # 批量读取线圈可能更高效，这里为了清晰分开读
        return {
            "x1_moving": self._read_bool(720),      # 1# X轴动作中
            "x2_moving": self._read_bool(721),      # 2# X轴动作中
            "rotation_moving": self._read_bool(722), # 旋转轴动作中
            "emergency_stop": self._read_bool(710)   # 急停按下
        }

    # ==============================
    # 3. 运动控制接口 (Actions)
    # ==============================

    def initialize_machine(self):
        """整机初始化 (地址 104)"""
        logger.info("Command: Machine Initialize")
        return self._write_bool(104, True)

    def move_axis(self, axis_id: int, target: float, speed: int = 1000):
        """
        通用轴移动控制
        :param axis_id: 1 (Top X), 2 (Bottom X), 3 (Rotation)
        :param target: 目标值 (mm 或 deg)
        :param speed: 速度值
        """
        if not self.connected: return False
        
        addr_speed = 0
        addr_target = 0
        addr_action = 0
        scale = 100.0 # 默认 0.01 精度

        if axis_id == 1: # 1# X
            addr_speed = 41190
            addr_target = 41212
            addr_action = 1010
        elif axis_id == 2: # 2# X
            addr_speed = 41290
            addr_target = 41312
            addr_action = 1110
        elif axis_id == 3: # Rotation
            addr_speed = 41390
            addr_target = 41412
            addr_action = 1210
        else:
            logger.error(f"Invalid Axis ID: {axis_id}")
            return False

        logger.info(f"Command: Move Axis {axis_id} to {target} at speed {speed}")

        # 1. 设置速度
        self._write_dint(addr_speed, speed)
        
        # 2. 设置目标位置
        target_val = int(target * scale)
        self._write_dint(addr_target, target_val)
        
        # 3. 触发动作
        self._write_bool(addr_action, True)
        return True

    def stop_all(self):
        """停止所有动作"""
        logger.info("Command: Stop All Actions")
        self._write_bool(1010, False)
        self._write_bool(1110, False)
        self._write_bool(1210, False)

    # ==============================
    # 4. 底层 Modbus 辅助方法
    # ==============================

    def _read_dint(self, address):
        """读取 32位 整数 (DInt)"""
        if not self.connected: return None
        try:
            # 读取 2 个寄存器
            rr = self.client.read_holding_registers(address, count=2, device_id=self.slave_id)
            if rr.isError(): return None
            
            # 手动解码: Word Order = Little (Low Reg, High Reg)
            # 假设 PLC 是 Little Endian Word Order (CDAB)
            # Reg0: Low Word, Reg1: High Word
            r0 = rr.registers[0]
            r1 = rr.registers[1]
            
            # 组合成 32位 int
            # val = (High << 16) | Low
            val = (r1 << 16) | r0
            
            # 处理符号位 (32位有符号整数)
            if val >= 0x80000000:
                val -= 0x100000000
                
            return val
        except Exception as e:
            logger.error(f"Read DInt Error {address}: {e}")
            return None

    def _write_dint(self, address, value):
        """写入 32位 整数 (DInt)"""
        if not self.connected: return False
        try:
            # 处理负数
            if value < 0:
                value += 0x100000000
                
            # 手动编码: Word Order = Little
            # Low Word
            r0 = value & 0xFFFF
            # High Word
            r1 = (value >> 16) & 0xFFFF
            
            payload = [r0, r1]
            
            self.client.write_registers(address, payload, device_id=self.slave_id)
            return True
        except Exception as e:
            logger.error(f"Write DInt Error {address}: {e}")
            return False

    def _read_bool(self, address):
        """读取线圈 (Bool)"""
        if not self.connected: return False
        try:
            rr = self.client.read_coils(address, count=1, device_id=self.slave_id)
            if rr.isError(): return False
            return rr.bits[0]
        except Exception:
            return False

    def _write_bool(self, address, value):
        """写入线圈 (Bool)"""
        if not self.connected: return False
        try:
            self.client.write_coil(address, value, device_id=self.slave_id)
            return True
        except Exception:
            return False

    def _read_register(self, address):
        """读取单个 16位 寄存器"""
        if not self.connected: return 0
        try:
            rr = self.client.read_holding_registers(address, count=1, device_id=self.slave_id)
            if rr.isError(): return 0
            return rr.registers[0]
        except Exception:
            return 0

    def _write_register(self, address, value):
        """写入单个 16位 寄存器"""
        if not self.connected: return False
        try:
            self.client.write_register(address, value, device_id=self.slave_id)
            return True
        except Exception:
            return False
