from pymodbus.datastore import ModbusServerContext, ModbusSequentialDataBlock
try:
    from pymodbus.datastore import ModbusSlaveContext
except ImportError:
    from pymodbus.datastore import ModbusDeviceContext as ModbusSlaveContext

store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0]*100),
    co=ModbusSequentialDataBlock(0, [0]*100),
    hr=ModbusSequentialDataBlock(0, [0]*100),
    ir=ModbusSequentialDataBlock(0, [0]*100)
)

try:
    print("Attempt 1: slaves=store")
    context = ModbusServerContext(slaves=store, single=True)
    print("Success 1")
except TypeError as e:
    print(f"Failed 1: {e}")

try:
    print("Attempt 2: positional")
    context = ModbusServerContext(store, single=True)
    print("Success 2")
except TypeError as e:
    print(f"Failed 2: {e}")
