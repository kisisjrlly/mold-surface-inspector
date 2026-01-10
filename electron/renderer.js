/**
 * 模具曲面精度分析系统 - Renderer 进程
 * 双探头检测系统可视化
 * 
 * 探头说明：
 * - 1#探头（绿色）：从左侧(-300mm)向中心(60mm)移动
 * - 2#探头（蓝色）：从右侧(300mm)向中心(-60mm)移动
 */

// ============== 全局变量 ==============
let ws = null;
let scene, camera, renderer, controls;
let pointCloud1, pointCloud2;  // 两个探头的点云
let moldMesh, rotatingGroup;
let carriage1Container, carriage2Container;  // 探头滑块容器
let isConnected = false;
let isScanning = false;
let pointCount = 0;

const MAX_POINTS = 100000;
const positions1 = new Float32Array(MAX_POINTS * 3);  // 1#探头点云
const positions2 = new Float32Array(MAX_POINTS * 3);  // 2#探头点云
const colors1 = new Float32Array(MAX_POINTS * 3);
const colors2 = new Float32Array(MAX_POINTS * 3);
let pointCount1 = 0, pointCount2 = 0;

// 误差统计数据
let errors = [];
let errorStats = {
    max: 0,
    min: 0,
    avg: 0,
    std: 0
};

// 机械参数 (与 simulation-of-device.html 一致)
const MOLD_RADIUS = 200;  // mm
const X1_START = -300, X1_END = 60;
const X2_START = 300, X2_END = -60;

// ============== DOM 元素 ==============
const connectionPanel = document.getElementById('connectionPanel');
const mainUI = document.getElementById('mainUI');
const connectBtn = document.getElementById('connectBtn');
const disconnectBtn = document.getElementById('disconnectBtn');
const connectionStatus = document.getElementById('connectionStatus');
const connectBtnText = document.getElementById('connectBtnText');

// ============== 连接管理 ==============
connectBtn.addEventListener('click', async () => {
    const plcIp = document.getElementById('plcIpInput').value.trim();
    const plcPort = parseInt(document.getElementById('plcPortInput').value);
    
    if (!plcIp || !plcPort || plcPort < 1 || plcPort > 65535) {
        showConnectionStatus('请填写正确的 IP 地址和端口号', 'error');
        return;
    }
    
    connectBtn.disabled = true;
    connectBtnText.textContent = '⏳ 正在启动服务...';
    
    try {
        const result = await window.electronAPI.startWSServer({ plcIp, plcPort });
        
        if (result.success) {
            showConnectionStatus('✅ ' + result.message, 'success');
            setTimeout(() => connectWebSocket(plcIp, plcPort), 1500);
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        showConnectionStatus('❌ 启动失败: ' + error.message, 'error');
        connectBtn.disabled = false;
        connectBtnText.textContent = '🔌 连接 PLC';
    }
});

disconnectBtn.addEventListener('click', async () => {
    if (ws) {
        ws.close();
        ws = null;
    }
    await window.electronAPI.stopWSServer();
    
    connectionPanel.classList.remove('hidden');
    mainUI.classList.add('hidden');
    isConnected = false;
    
    connectBtn.disabled = false;
    connectBtnText.textContent = '🔌 连接 PLC';
});

function connectWebSocket(plcIp, plcPort) {
    connectBtnText.textContent = '🔄 正在连接 WebSocket...';
    
    ws = new WebSocket('ws://127.0.0.1:8765');
    
    ws.onopen = () => {
        console.log('✅ WebSocket 已连接');
        
        document.getElementById('status-indicator').className = 'status-indicator status-connected';
        document.getElementById('status-text').textContent = '已连接';
        document.getElementById('connectedPlcIp').textContent = plcIp;
        document.getElementById('connectedPlcPort').textContent = plcPort;
        
        connectionPanel.classList.add('hidden');
        mainUI.classList.remove('hidden');
        isConnected = true;
        
        initThreeJS();
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWSMessage(data);
        } catch (e) {
            console.error('消息解析失败:', e);
        }
    };
    
    ws.onerror = (error) => {
        console.error('❌ WebSocket 错误:', error);
        showConnectionStatus('WebSocket 连接失败', 'error');
        connectBtn.disabled = false;
        connectBtnText.textContent = '🔌 连接 PLC';
    };
    
    ws.onclose = () => {
        console.log('⚠️ WebSocket 已断开');
        if (isConnected) {
            document.getElementById('status-indicator').className = 'status-indicator status-disconnected';
            document.getElementById('status-text').textContent = '连接断开';
            isConnected = false;
        }
    };
}

function showConnectionStatus(message, type) {
    connectionStatus.textContent = message;
    connectionStatus.className = `alert ${
        type === 'success' ? 'alert-success' : 
        type === 'error' ? 'alert-error' : 'alert-info'
    }`;
    connectionStatus.classList.remove('hidden');
}

window.electronAPI.onWSServerStopped(() => {
    if (isConnected) {
        alert('⚠️ Python 服务器意外停止');
        disconnectBtn.click();
    }
});

// ============== WebSocket 消息处理 ==============
function handleWSMessage(msg) {
    switch (msg.type) {
        case 'position':
            updatePosition(msg.x1, msg.x2, msg.rot);
            if (msg.phase) updatePhase(msg.phase);
            if (msg.pointCount !== undefined) {
                document.getElementById('pointCount').textContent = msg.pointCount;
            }
            break;
        
        case 'point':
            addPoint(msg.probe, msg.x, msg.y, msg.z, msg.error);
            break;
        
        case 'status':
            updateStatus(msg);
            break;
    }
}

function updatePosition(x1, x2, rot) {
    document.getElementById('x1Pos').textContent = x1.toFixed(2);
    document.getElementById('x2Pos').textContent = x2.toFixed(2);
    document.getElementById('rotPos').textContent = rot.toFixed(1);
    
    // 更新进度条
    const progress1 = Math.min(100, Math.max(0, ((x1 - X1_START) / (X1_END - X1_START)) * 100));
    const progress2 = Math.min(100, Math.max(0, ((X2_START - x2) / (X2_START - X2_END)) * 100));
    
    document.getElementById('x1Progress').style.width = progress1 + '%';
    document.getElementById('x2Progress').style.width = progress2 + '%';
    
    // 调试日志 - 每秒输出一次
    if (!window.lastLogTime || Date.now() - window.lastLogTime > 1000) {
        console.log(`🔄 位置更新: 1#=${x1.toFixed(1)}mm, 2#=${x2.toFixed(1)}mm, 旋转=${rot.toFixed(1)}°`);
        console.log(`📦 容器状态: carriage1=${!!carriage1Container}, carriage2=${!!carriage2Container}, rotating=${!!rotatingGroup}`);
        window.lastLogTime = Date.now();
    }
    
    // 更新3D模型 - 旋转主轴
    if (rotatingGroup) {
        rotatingGroup.rotation.x = THREE.MathUtils.degToRad(rot);
    } else {
        console.error('❌ rotatingGroup 未初始化');
    }
    
    // 更新3D模型 - 探头位置
    if (carriage1Container) {
        const oldX = carriage1Container.position.x;
        carriage1Container.position.x = x1;
        if (Math.abs(x1 - oldX) > 1) {
            console.log(`🟢 1#探头移动: ${oldX.toFixed(1)} → ${x1.toFixed(1)}mm`);
        }
    } else {
        console.error('❌ carriage1Container 未初始化');
    }
    if (carriage2Container) {
        const oldX = carriage2Container.position.x;
        carriage2Container.position.x = x2;
        if (Math.abs(x2 - oldX) > 1) {
            console.log(`🔵 2#探头移动: ${oldX.toFixed(1)} → ${x2.toFixed(1)}mm`);
        }
    } else {
        console.error('❌ carriage2Container 未初始化');
    }
}

function updatePhase(phase) {
    const phaseTexts = {
        'IDLE': '待机',
        'APPROACH': 'X轴归位中...',
        'SCAN': '翻转扫描中...',
        'STEP': 'X轴进给...',
        'COMPLETE': '检测完成',
        'RESET': '复位中...',
        'ERROR': '错误'
    };
    
    const phaseColors = {
        'IDLE': 'text-gray-400',
        'APPROACH': 'text-blue-400',
        'SCAN': 'text-green-400',
        'STEP': 'text-yellow-400',
        'COMPLETE': 'text-green-500',
        'RESET': 'text-orange-400',
        'ERROR': 'text-red-500'
    };
    
    const phaseEl = document.getElementById('scanPhase');
    if (phaseEl) {
        phaseEl.textContent = phaseTexts[phase] || phase;
        phaseEl.className = 'font-mono ' + (phaseColors[phase] || '');
    }
}

function updateStatus(msg) {
    if (msg.scanning !== undefined) {
        isScanning = msg.scanning;
        
        if (isScanning) {
            document.getElementById('status-indicator').className = 'status-indicator status-scanning';
            document.getElementById('status-text').textContent = msg.text || '扫描中...';
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
        } else {
            document.getElementById('status-indicator').className = 'status-indicator status-connected';
            document.getElementById('status-text').textContent = msg.text || '已连接';
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
        }
    }
    
    if (msg.phase) updatePhase(msg.phase);
    if (msg.pointCount !== undefined) {
        document.getElementById('pointCount').textContent = msg.pointCount;
    }
}

function addPoint(probe, x, y, z, error) {
    // 记录误差用于统计
    errors.push(error);
    updateErrorStats();
    
    // 根据误差计算颜色 - 增强对比度
    const absError = Math.abs(error);
    let r, g, b;
    if (absError <= 0.05) {
        // 绿色 - 合格 (鲜艳绿)
        r = 0.0; g = 1.0; b = 0.3;
    } else if (absError <= 0.10) {
        // 黄色 - 注意 (明亮黄)
        r = 1.0; g = 0.9; b = 0.0;
    } else {
        // 红色 - 超差 (鲜艳红)
        r = 1.0; g = 0.0; b = 0.0;
    }
    
    if (probe === 1) {
        // 1#探头 - 保持误差颜色，不做探头颜色偏移
        if (pointCount1 >= MAX_POINTS) return;
        const i = pointCount1;
        positions1[i * 3] = x;
        positions1[i * 3 + 1] = y;
        positions1[i * 3 + 2] = z;
        // 直接使用误差颜色，不做偏移以保持颜色准确性
        colors1[i * 3] = r;
        colors1[i * 3 + 1] = g;
        colors1[i * 3 + 2] = b;
        pointCount1++;
        
        if (pointCloud1) {
            pointCloud1.geometry.setDrawRange(0, pointCount1);
            pointCloud1.geometry.attributes.position.needsUpdate = true;
            pointCloud1.geometry.attributes.color.needsUpdate = true;
        }
    } else {
        // 2#探头 - 保持误差颜色，不做探头颜色偏移
        if (pointCount2 >= MAX_POINTS) return;
        const i = pointCount2;
        positions2[i * 3] = x;
        positions2[i * 3 + 1] = y;
        positions2[i * 3 + 2] = z;
        // 直接使用误差颜色，不做偏移以保持颜色准确性
        colors2[i * 3] = r;
        colors2[i * 3 + 1] = g;
        colors2[i * 3 + 2] = b;
        pointCount2++;
        
        if (pointCloud2) {
            pointCloud2.geometry.setDrawRange(0, pointCount2);
            pointCloud2.geometry.attributes.position.needsUpdate = true;
            pointCloud2.geometry.attributes.color.needsUpdate = true;
        }
    }
    
    pointCount = pointCount1 + pointCount2;
    
    // 添加到数据表格（最多显示最近100条）
    addToDataTable(probe, x, y, z, error);
}

function updateErrorStats() {
    if (errors.length === 0) return;
    
    // 计算统计数据
    errorStats.max = Math.max(...errors);
    errorStats.min = Math.min(...errors);
    errorStats.avg = errors.reduce((a, b) => a + b, 0) / errors.length;
    
    // 计算标准差
    const variance = errors.reduce((sum, val) => sum + Math.pow(val - errorStats.avg, 2), 0) / errors.length;
    errorStats.std = Math.sqrt(variance);
    
    // 更新显示
    const maxEl = document.getElementById('errorMax');
    const minEl = document.getElementById('errorMin');
    const avgEl = document.getElementById('errorAvg');
    const stdEl = document.getElementById('errorStd');
    
    if (maxEl) maxEl.textContent = (errorStats.max >= 0 ? '+' : '') + errorStats.max.toFixed(3);
    if (minEl) minEl.textContent = errorStats.min.toFixed(3);
    if (avgEl) avgEl.textContent = errorStats.avg.toFixed(3);
    if (stdEl) stdEl.textContent = errorStats.std.toFixed(3);
}

function addToDataTable(probe, x, y, z, error) {
    const tbody = document.getElementById('dataTableBody');
    if (!tbody) return;
    
    // 首次添加时清除占位文本
    if (tbody.children.length === 1 && tbody.children[0].children.length === 1) {
        tbody.innerHTML = '';
    }
    
    // 限制表格行数（保留最新100条）
    if (tbody.children.length >= 100) {
        tbody.removeChild(tbody.firstChild);
    }
    
    // 根据误差值确定颜色类
    let errorClass = 'error-good';
    if (Math.abs(error) > 0.10) errorClass = 'error-bad';
    else if (Math.abs(error) > 0.05) errorClass = 'error-warn';
    
    const row = tbody.insertRow();
    row.innerHTML = `
        <td><span class="probe-badge probe-${probe}">${probe}#</span></td>
        <td>${x.toFixed(2)}</td>
        <td>${y.toFixed(2)}</td>
        <td>${z.toFixed(2)}</td>
        <td class="${errorClass}">${(error >= 0 ? '+' : '') + error.toFixed(3)}</td>
    `;
    
    // 自动滚动到底部
    tbody.parentElement.parentElement.scrollTop = tbody.parentElement.parentElement.scrollHeight;
}

// ============== Three.js 初始化 ==============
function initThreeJS() {
    const container = document.getElementById('three-container');
    if (!container) {
        console.error('找不到 three-container 元素');
        return;
    }
    
    // 场景
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x181818);
    scene.fog = new THREE.FogExp2(0x181818, 0.0008);
    
    // 相机
    camera = new THREE.PerspectiveCamera(
        40,
        container.clientWidth / container.clientHeight,
        1,
        10000
    );
    camera.position.set(600, 400, 800);
    
    // 渲染器
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.outputEncoding = THREE.sRGBEncoding;
    container.appendChild(renderer.domElement);
    
    // 控制器
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 1.5;
    controls.target.set(0, 0, 0);
    
    // 灯光系统 (与仿真一致)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);
    
    const mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
    mainLight.position.set(200, 500, 200);
    mainLight.castShadow = true;
    scene.add(mainLight);
    
    const bottomLight = new THREE.PointLight(0x4455ff, 0.5);
    bottomLight.position.set(0, -200, 0);
    scene.add(bottomLight);
    
    // 网格
    const gridHelper = new THREE.GridHelper(2000, 40, 0x444444, 0x222222);
    gridHelper.position.y = -300;
    scene.add(gridHelper);
    
    // 创建旋转组（模具和探头轨迹）
    rotatingGroup = new THREE.Group();
    scene.add(rotatingGroup);
    
    // 创建完整设备模型
    createMachineModel();
    
    // 创建模具（半圆柱）
    createMold();
    
    // 创建点云
    createPointClouds();
    
    // 启动渲染循环
    animate();
    
    // 输出初始化确认
    console.log('✅ Three.js 初始化完成');
    console.log(`📦 模型状态:`);
    console.log(`  - rotatingGroup: ${!!rotatingGroup}`);
    console.log(`  - carriage1Container: ${!!carriage1Container}, 初始位置X=${carriage1Container?.position.x}`);
    console.log(`  - carriage2Container: ${!!carriage2Container}, 初始位置X=${carriage2Container?.position.x}`);
    console.log(`  - pointCloud1: ${!!pointCloud1}`);
    console.log(`  - pointCloud2: ${!!pointCloud2}`);
    
    // 窗口大小调整
    window.addEventListener('resize', () => {
        const width = container.clientWidth;
        const height = container.clientHeight;
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
    });
}

// ============== 设备3D模型构建 ==============
function createMachineModel() {
    // 材质库 (与 simulation-of-device.html 一致)
    const materials = {
        framePaint: new THREE.MeshStandardMaterial({ color: 0x505050, roughness: 0.7, metalness: 0.2 }),
        steelShiny: new THREE.MeshStandardMaterial({ color: 0xaaaaaa, roughness: 0.2, metalness: 0.9 }),
        steelMatte: new THREE.MeshStandardMaterial({ color: 0x777777, roughness: 0.6, metalness: 0.6 }),
        railBlack: new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.4, metalness: 0.1 }),
        anodizedBlack: new THREE.MeshStandardMaterial({ color: 0x222222, roughness: 0.5, metalness: 0.5 }),
        probeBody: new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.2, metalness: 0.1 }),
        indicatorTip: new THREE.MeshStandardMaterial({ color: 0xff3333, emissive: 0xaa0000, emissiveIntensity: 0.2 }),
        probe1Color: new THREE.MeshStandardMaterial({ color: 0x4ade80 }), // 绿色
        probe2Color: new THREE.MeshStandardMaterial({ color: 0x60a5fa })  // 蓝色
    };
    
    // 机架组
    const machineGroup = new THREE.Group();
    scene.add(machineGroup);
    
    // 1. 机架 (Frame)
    const frameGroup = new THREE.Group();
    const frameWidth = 750, frameHeight = 450;
    
    // 左侧支撑板
    const leftPlate = new THREE.Mesh(
        new THREE.BoxGeometry(40, frameHeight, 200),
        materials.framePaint
    );
    leftPlate.position.set(-frameWidth/2, 0, 0);
    frameGroup.add(leftPlate);
    
    // 右侧支撑板
    const rightPlate = new THREE.Mesh(
        new THREE.BoxGeometry(40, frameHeight, 40),
        materials.framePaint
    );
    rightPlate.position.set(frameWidth/2, 0, 0);
    frameGroup.add(rightPlate);
    
    // 底部横梁
    const bottomBeam = new THREE.Mesh(
        new THREE.BoxGeometry(frameWidth + 80, 40, 40),
        materials.framePaint
    );
    bottomBeam.position.set(0, -frameHeight/2, 0);
    frameGroup.add(bottomBeam);
    
    machineGroup.add(frameGroup);
    
    // 2. 旋转总成
    // 主轴
    const mainShaft = new THREE.Mesh(
        new THREE.CylinderGeometry(35, 35, 600, 32),
        materials.steelShiny
    );
    mainShaft.rotation.z = Math.PI / 2;
    rotatingGroup.add(mainShaft);
    
    // 左侧轴
    const leftShaft = new THREE.Mesh(
        new THREE.CylinderGeometry(25, 25, 100, 32),
        materials.steelShiny
    );
    leftShaft.rotation.z = Math.PI / 2;
    leftShaft.position.x = -350;
    rotatingGroup.add(leftShaft);
    
    // 右侧轴
    const rightShaft = new THREE.Mesh(
        new THREE.CylinderGeometry(25, 25, 150, 32),
        materials.steelShiny
    );
    rightShaft.rotation.z = Math.PI / 2;
    rightShaft.position.x = 375;
    rotatingGroup.add(rightShaft);
    
    // 轴承座
    const bearingL = new THREE.Mesh(
        new THREE.BoxGeometry(50, 80, 80),
        materials.steelMatte
    );
    bearingL.position.x = -375;
    machineGroup.add(bearingL);
    
    const bearingR = new THREE.Mesh(
        new THREE.BoxGeometry(50, 80, 80),
        materials.steelMatte
    );
    bearingR.position.x = 375;
    machineGroup.add(bearingR);
    
    // 电机联轴器
    const motorCoupling = new THREE.Mesh(
        new THREE.CylinderGeometry(30, 30, 60, 32),
        materials.framePaint
    );
    motorCoupling.rotation.z = Math.PI / 2;
    motorCoupling.position.x = 430;
    machineGroup.add(motorCoupling);
    
    // 伺服电机
    const servoMotor = new THREE.Mesh(
        new THREE.BoxGeometry(80, 80, 120),
        materials.anodizedBlack
    );
    servoMotor.position.x = 520;
    machineGroup.add(servoMotor);
    
    // 3. 导轨系统
    const railLength = 700;
    const railOffset = 35;
    
    // 上导轨 (1#探头)
    const topMount = new THREE.Mesh(
        new THREE.BoxGeometry(railLength, 10, 50),
        materials.steelMatte
    );
    topMount.position.y = railOffset + 5;
    rotatingGroup.add(topMount);
    
    const topRail = new THREE.Mesh(
        new THREE.BoxGeometry(railLength, 5, 20),
        materials.railBlack
    );
    topRail.position.y = railOffset + 12.5;
    rotatingGroup.add(topRail);
    
    // 下导轨 (2#探头)
    const botMount = new THREE.Mesh(
        new THREE.BoxGeometry(railLength, 10, 50),
        materials.steelMatte
    );
    botMount.position.y = -(railOffset + 5);
    rotatingGroup.add(botMount);
    
    const botRail = new THREE.Mesh(
        new THREE.BoxGeometry(railLength, 5, 20),
        materials.railBlack
    );
    botRail.position.y = -(railOffset + 12.5);
    rotatingGroup.add(botRail);
    
    // 4. 探头组件
    function createProbeAssembly(colorMat, isTop) {
        const group = new THREE.Group();
        const sign = isTop ? 1 : -1;
        
        // 滑块本体
        const block = new THREE.Mesh(
            new THREE.BoxGeometry(60, 15, 40),
            colorMat
        );
        group.add(block);
        
        // 支架
        const holder = new THREE.Mesh(
            new THREE.BoxGeometry(20, 40, 20),
            materials.steelMatte
        );
        holder.position.y = sign * 20;
        group.add(holder);
        
        // 表盘本体
        const dialBody = new THREE.Mesh(
            new THREE.CylinderGeometry(15, 15, 10, 32),
            materials.probeBody
        );
        dialBody.rotation.x = Math.PI / 2;
        dialBody.position.y = sign * 40;
        dialBody.position.z = 10;
        group.add(dialBody);
        
        // 测量杆
        const stem = new THREE.Mesh(
            new THREE.CylinderGeometry(3, 3, 40, 16),
            materials.steelShiny
        );
        stem.position.y = sign * 50;
        stem.position.z = 10;
        group.add(stem);
        
        // 测头
        const tip = new THREE.Mesh(
            new THREE.SphereGeometry(3),
            materials.indicatorTip
        );
        tip.position.y = sign * 70;
        tip.position.z = 10;
        group.add(tip);
        
        return group;
    }
    
    // 1#探头 (上方，绿色)
    const carriage1 = createProbeAssembly(materials.probe1Color, true);
    carriage1Container = new THREE.Group();
    carriage1Container.position.y = railOffset + 20;
    carriage1Container.position.x = 0;  // 初始位置
    carriage1Container.add(carriage1);
    rotatingGroup.add(carriage1Container);
    
    // 2#探头 (下方，蓝色)
    const carriage2 = createProbeAssembly(materials.probe2Color, false);
    carriage2Container = new THREE.Group();
    carriage2Container.position.y = -(railOffset + 20);
    carriage2Container.position.x = 0;  // 初始位置
    carriage2Container.add(carriage2);
    rotatingGroup.add(carriage2Container);
}

function createMold() {
    // 半圆柱模具 (与 simulation-of-device.html 一致)
    const moldGeometry = new THREE.CylinderGeometry(
        MOLD_RADIUS, MOLD_RADIUS, 
        700,  // 长度
        64, 1, true,
        Math.PI * 0.15, Math.PI * 0.7
    );
    
    const moldMaterial = new THREE.MeshStandardMaterial({
        color: 0xcccccc,
        metalness: 0.3,
        roughness: 0.2,
        transparent: true,
        opacity: 0.4,
        side: THREE.DoubleSide,
        depthWrite: false
    });
    
    moldMesh = new THREE.Mesh(moldGeometry, moldMaterial);
    moldMesh.rotation.z = Math.PI / 2;
    moldMesh.rotation.x = Math.PI;
    moldMesh.position.y = 20;
    scene.add(moldMesh);  // 模具固定在场景中，不随旋转组旋转
    
    // 线框辅助
    const wireframeMat = new THREE.MeshBasicMaterial({
        color: 0x3b82f6,
        wireframe: true,
        transparent: true,
        opacity: 0.15
    });
    const wireframeMesh = new THREE.Mesh(moldGeometry.clone(), wireframeMat);
    wireframeMesh.rotation.z = Math.PI / 2;
    wireframeMesh.rotation.x = Math.PI;
    wireframeMesh.position.y = 20;
    scene.add(wireframeMesh);  // 线框也固定在场景中
}

function createPointClouds() {
    // 1#探头点云 - 使用误差颜色编码
    const geometry1 = new THREE.BufferGeometry();
    geometry1.setAttribute('position', new THREE.BufferAttribute(positions1, 3));
    geometry1.setAttribute('color', new THREE.BufferAttribute(colors1, 3));
    geometry1.setDrawRange(0, 0);
    
    const material1 = new THREE.PointsMaterial({
        size: 5,  // 增大点尺寸以便看清颜色
        vertexColors: true,
        sizeAttenuation: true
    });
    
    pointCloud1 = new THREE.Points(geometry1, material1);
    scene.add(pointCloud1);
    
    // 2#探头点云 - 使用误差颜色编码
    const geometry2 = new THREE.BufferGeometry();
    geometry2.setAttribute('position', new THREE.BufferAttribute(positions2, 3));
    geometry2.setAttribute('color', new THREE.BufferAttribute(colors2, 3));
    geometry2.setDrawRange(0, 0);
    
    const material2 = new THREE.PointsMaterial({
        size: 5,  // 增大点尺寸以便看清颜色
        vertexColors: true,
        sizeAttenuation: true
    });
    
    pointCloud2 = new THREE.Points(geometry2, material2);
    scene.add(pointCloud2);
}

function animate() {
    requestAnimationFrame(animate);
    if (controls) controls.update();
    if (renderer && scene && camera) {
        renderer.render(scene, camera);
    }
}

// ============== 视角控制 ==============
window.setView = function(view) {
    if (!camera || !controls) return;
    
    switch (view) {
        case 'front':
            camera.position.set(0, 0, 1000);
            controls.target.set(0, 0, 0);
            break;
        case 'top':
            camera.position.set(0, 1000, 0);
            controls.target.set(0, 0, 0);
            break;
        case 'side':
            camera.position.set(1000, 0, 0);
            controls.target.set(0, 0, 0);
            break;
        case 'iso':
            camera.position.set(600, 400, 800);
            controls.target.set(0, 0, 0);
            break;
    }
};

// ============== 扫描控制 ==============
document.getElementById('startBtn').addEventListener('click', () => {
    if (!ws || !isConnected) {
        alert('请先连接 PLC');
        return;
    }
    
    const params = {
        stepX: parseFloat(document.getElementById('stepX').value) || 10,
        maxAngle: parseFloat(document.getElementById('maxAngle').value) || 170,
        angleStep: parseFloat(document.getElementById('angleStep').value) || 2.5
    };
    
    // 清空点云
    pointCount1 = 0;
    pointCount2 = 0;
    pointCount = 0;
    if (pointCloud1) pointCloud1.geometry.setDrawRange(0, 0);
    if (pointCloud2) pointCloud2.geometry.setDrawRange(0, 0);
    
    ws.send(JSON.stringify({ cmd: 'start_scan', ...params }));
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
});

document.getElementById('stopBtn').addEventListener('click', () => {
    if (ws) {
        ws.send(JSON.stringify({ cmd: 'stop_scan' }));
    }
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
});

document.getElementById('resetBtn').addEventListener('click', () => {
    if (ws) {
        ws.send(JSON.stringify({ cmd: 'reset' }));
    }
    // 清空点云和统计数据
    pointCount1 = 0;
    pointCount2 = 0;
    pointCount = 0;
    errors = [];
    errorStats = { max: 0, min: 0, avg: 0, std: 0 };
    
    if (pointCloud1) pointCloud1.geometry.setDrawRange(0, 0);
    if (pointCloud2) pointCloud2.geometry.setDrawRange(0, 0);
    
    document.getElementById('pointCount').textContent = '0';
    document.getElementById('errorMax').textContent = '+0.000';
    document.getElementById('errorMin').textContent = '0.000';
    document.getElementById('errorAvg').textContent = '0.000';
    document.getElementById('errorStd').textContent = '0.000';
    
    // 清空数据表格并恢复占位文本
    const tbody = document.getElementById('dataTableBody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="5" style="color: #64748b; padding: 20px;">等待扫描数据...</td></tr>';
    }
});
