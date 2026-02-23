"""
测试千分表读取 - 诊断脚本
直接从PLC读取探头测量数据，用于诊断读取问题
"""

import sys
from pymodbus.client import ModbusTcpClient

def test_probe_read(ip='192.168.1.100', port=502):
    print(f"连接到 PLC: {ip}:{port}")
    client = ModbusTcpClient(ip, port=port)
    
    if not client.connect():
        print("❌ 连接失败!")
        return
    
    print("✅ 连接成功!\n")
    
    # 测试不同的地址和读取方式
    test_addresses = [
        (110, "1#测距数值 (协议地址110)"),
        (112, "2#测距数值 (协议地址112)"),
        (109, "尝试地址109 (110-1)"),
        (111, "尝试地址111 (112-1)"),
    ]
    
    print("=" * 60)
    print("测试 read_holding_registers (功能码3)")
    print("=" * 60)
    
    for addr, desc in test_addresses:
        try:
            result = client.read_holding_registers(addr, count=2, device_id=1)
            if result.isError():
                print(f"  {desc}: ❌ 错误 - {result}")
            else:
                r0 = result.registers[0]
                r1 = result.registers[1]
                # Little Endian
                val_le = (r1 << 16) | r0
                # Big Endian
                val_be = (r0 << 16) | r1
                print(f"  {desc}:")
                print(f"    Reg0={r0} (0x{r0:04X}), Reg1={r1} (0x{r1:04X})")
                print(f"    Little Endian: {val_le} -> {val_le * 0.01:.2f}mm")
                print(f"    Big Endian:    {val_be} -> {val_be * 0.01:.2f}mm")
        except Exception as e:
            print(f"  {desc}: ❌ 异常 - {e}")
    
    print("\n" + "=" * 60)
    print("测试 read_input_registers (功能码4)")
    print("=" * 60)
    
    for addr, desc in test_addresses:
        try:
            result = client.read_input_registers(addr, count=2, device_id=1)
            if result.isError():
                print(f"  {desc}: ❌ 错误 - {result}")
            else:
                r0 = result.registers[0]
                r1 = result.registers[1]
                val_le = (r1 << 16) | r0
                val_be = (r0 << 16) | r1
                print(f"  {desc}:")
                print(f"    Reg0={r0} (0x{r0:04X}), Reg1={r1} (0x{r1:04X})")
                print(f"    Little Endian: {val_le} -> {val_le * 0.01:.2f}mm")
                print(f"    Big Endian:    {val_be} -> {val_be * 0.01:.2f}mm")
        except Exception as e:
            print(f"  {desc}: ❌ 异常 - {e}")
    
    print("\n" + "=" * 60)
    print("测试批量读取 (地址 100-120)")
    print("=" * 60)
    
    try:
        result = client.read_holding_registers(100, count=20, device_id=1)
        if result.isError():
            print(f"❌ 错误 - {result}")
        else:
            print("地址范围 100-119 的值:")
            for i, val in enumerate(result.registers):
                if val != 0:  # 只显示非零值
                    print(f"  地址 {100+i}: {val} (0x{val:04X})")
    except Exception as e:
        print(f"❌ 异常 - {e}")
    
    client.close()
    print("\n连接已关闭")

if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 502
    test_probe_read(ip, port)
