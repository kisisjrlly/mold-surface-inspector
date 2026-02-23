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
let theoreticalPointCloud;     // 理论点云
let rotatingGroup;
let carriage1Container, carriage2Container;  // 探头滑块容器
let isConnected = false;
let isScanning = false;
let pointCount = 0;
let theoreticalLoaded = false;

// IP地址历史记录（最多保存2个不同的IP）
const IP_HISTORY_KEY = 'plc_ip_history';
const MAX_IP_HISTORY = 2;

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

// 机械参数 - 根据实际被测曲面尺寸
// 实际曲面尺寸: X: 1409.632mm, Y: 796.111mm, Z: 599.526mm
const MOLD_RADIUS = 400;  // mm，模具半径约为Y/2
const MOLD_LENGTH = 1410; // mm，模具长度（X方向）
const X1_START = -700, X1_END = 100;   // 1#探头行程（覆盖半个模具+重叠区）
const X2_START = 700, X2_END = -100;   // 2#探头行程

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
        
        // 保存IP到历史记录
        saveIPToHistory(plcIp);
        
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
            // 更新千分表测量值
            if (msg.probe1 !== undefined) {
                document.getElementById('probe1Value').textContent = msg.probe1.toFixed(2);
            }
            if (msg.probe2 !== undefined) {
                document.getElementById('probe2Value').textContent = msg.probe2.toFixed(2);
            }
            break;
        
        case 'point':
            addPoint(msg.probe, msg.x, msg.y, msg.z, msg.error);
            break;
        
        case 'status':
            updateStatus(msg);
            break;
        
        case 'theoretical_load_result':
            handleTheoreticalLoadResult(msg);
            break;
    }
}

function handleTheoreticalLoadResult(msg) {
    const fileNameEl = document.getElementById('theoreticalFileName');
    const pointCountEl = document.getElementById('theoreticalPointCount');
    
    if (msg.success) {
        theoreticalLoaded = true;
        fileNameEl.textContent = `✅ 已加载`;
        pointCountEl.textContent = `共 ${msg.pointCount} 个理论点`;
        
        // 在 3D 场景中显示理论点云
        if (msg.points && msg.points.length > 0) {
            displayTheoreticalPoints(msg.points);
        }
        
        console.log('理论点云加载成功:', msg.pointCount, '个点');
    } else {
        fileNameEl.textContent = `❌ ${msg.message}`;
        pointCountEl.textContent = '';
        console.error('理论点云加载失败:', msg.message);
    }
}

function displayTheoreticalPoints(points) {
    // 移除之前的理论点云
    if (theoreticalPointCloud) {
        scene.remove(theoreticalPointCloud);
        theoreticalPointCloud.geometry.dispose();
        theoreticalPointCloud.material.dispose();
    }
    
    // 创建理论点云几何体
    const geometry = new THREE.BufferGeometry();
    
    // 显示全部点，不采样（数据量不大）
    const actualCount = points.length;
    
    const positions = new Float32Array(actualCount * 3);
    const colors = new Float32Array(actualCount * 3);
    
    // 计算点云中心和范围
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;
    
    for (let i = 0; i < points.length; i++) {
        const point = points[i];
        minX = Math.min(minX, point[0]);
        maxX = Math.max(maxX, point[0]);
        minY = Math.min(minY, point[1]);
        maxY = Math.max(maxY, point[1]);
        minZ = Math.min(minZ, point[2]);
        maxZ = Math.max(maxZ, point[2]);
    }
    
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const centerZ = (minZ + maxZ) / 2;
    
    console.log(`点云原始范围: X=[${minX.toFixed(1)}, ${maxX.toFixed(1)}], Y=[${minY.toFixed(1)}, ${maxY.toFixed(1)}], Z=[${minZ.toFixed(1)}, ${maxZ.toFixed(1)}]`);
    
    for (let i = 0; i < points.length; i++) {
        const point = points[i];
        // 坐标变换使曲面开口朝上：
        // 原始数据: X是长度方向, Y是宽度方向, Z是高度方向
        // 变换后: X不变, Y向上(原Z), Z向前(原-Y)
        
        const x = point[0] - centerX;  // X保持，平移到中心
        const y = point[2] - centerZ;  // 原Z变成Y（向上）
        const z = -(point[1] - centerY); // 原Y变成-Z（向前）
        
        positions[i * 3] = x;
        positions[i * 3 + 1] = y;
        positions[i * 3 + 2] = z;
        
        // 理论点云使用浅蓝色，与测量点的绿/黄/红区分
        colors[i * 3] = 0.3;
        colors[i * 3 + 1] = 0.7;
        colors[i * 3 + 2] = 1.0;
    }
    
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    
    const material = new THREE.PointsMaterial({
        size: 5,  // 大点尺寸
        vertexColors: true,
        transparent: false,  // 不透明，更清晰
        sizeAttenuation: true
    });
    
    theoreticalPointCloud = new THREE.Points(geometry, material);
    scene.add(theoreticalPointCloud);
    
    // 计算变换后的边界
    geometry.computeBoundingBox();
    const box = geometry.boundingBox;
    const center = new THREE.Vector3();
    box.getCenter(center);
    
    // 更新相机目标位置
    controls.target.copy(center);
    
    // 计算合适的相机距离，从斜上方观察
    const size = new THREE.Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z);
    camera.position.set(center.x + maxDim * 0.8, center.y + maxDim * 0.6, center.z + maxDim * 0.8);
    controls.update();
    
    console.log(`显示理论点云: ${actualCount} 个点`);
    console.log(`变换后边界: X=[${box.min.x.toFixed(1)}, ${box.max.x.toFixed(1)}], Y=[${box.min.y.toFixed(1)}, ${box.max.y.toFixed(1)}], Z=[${box.min.z.toFixed(1)}, ${box.max.z.toFixed(1)}]`);
}

function updatePosition(x1, x2, rot) {
    document.getElementById('x1Pos').textContent = x1.toFixed(2);
    document.getElementById('x2Pos').textContent = x2.toFixed(2);
    document.getElementById('rotPos').textContent = rot.toFixed(1);
    
    // 更新手动操作面板的位置显示
    updateManualPositionDisplay(x1, x2, rot);
    
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
            // 根据阶段显示不同状态
            if (msg.phase === 'COMPLETE') {
                document.getElementById('status-indicator').className = 'status-indicator status-complete';
                document.getElementById('status-text').textContent = msg.text || '扫描完成';
                // 显示完成提示
                console.log('🎉 扫描完成!', msg.pointCount, '个点');
            } else {
                document.getElementById('status-indicator').className = 'status-indicator status-connected';
                document.getElementById('status-text').textContent = msg.text || '已连接';
            }
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
        }
    }
    
    if (msg.phase) updatePhase(msg.phase);
    if (msg.pointCount !== undefined) {
        document.getElementById('pointCount').textContent = msg.pointCount;
    }
}

// 批量更新计数器，用于减少频繁更新
let pendingPointUpdates = 0;
const BATCH_UPDATE_THRESHOLD = 10;  // 每10个点更新一次

function addPoint(probe, x, y, z, error) {
    // 记录误差用于统计（限制数组大小防止内存溢出）
    if (errors.length < 50000) {
        errors.push(error);
    }
    
    // 每10个点更新一次统计
    pendingPointUpdates++;
    if (pendingPointUpdates >= BATCH_UPDATE_THRESHOLD) {
        updateErrorStats();
        pendingPointUpdates = 0;
    }
    
    // 根据误差计算颜色 - 使用鲜艳的绿/橙/红色
    const absError = Math.abs(error);
    let r, g, b;
    if (absError <= 0.05) {
        // 绿色 - 合格 (鲜亮绿)
        r = 0.1; g = 0.9; b = 0.1;
    } else if (absError <= 0.10) {
        // 橙色 - 注意 (明亮橙)
        r = 1.0; g = 0.5; b = 0.0;
    } else {
        // 红色 - 超差 (鲜艳红)
        r = 1.0; g = 0.0; b = 0.0;
    }
    
    // 坐标变换：与理论点云保持一致
    // 后端发送的数据: x=探头位置, y=radius*sin(angle)向上, z=radius*cos(angle)向前
    // Three.js中: X轴向右, Y轴向上, Z轴向前
    // 直接使用后端坐标，无需额外变换
    const displayX = x;
    const displayY = y;   // Y向上
    const displayZ = z;   // Z向前
    
    if (probe === 1) {
        // 1#探头
        if (pointCount1 >= MAX_POINTS) return;
        const i = pointCount1;
        positions1[i * 3] = displayX;
        positions1[i * 3 + 1] = displayY;
        positions1[i * 3 + 2] = displayZ;
        colors1[i * 3] = r;
        colors1[i * 3 + 1] = g;
        colors1[i * 3 + 2] = b;
        pointCount1++;
        
        // 每次都更新点云显示
        if (pointCloud1) {
            pointCloud1.geometry.setDrawRange(0, pointCount1);
            pointCloud1.geometry.attributes.position.needsUpdate = true;
            pointCloud1.geometry.attributes.color.needsUpdate = true;
        }
    } else {
        // 2#探头
        if (pointCount2 >= MAX_POINTS) return;
        const i = pointCount2;
        positions2[i * 3] = displayX;
        positions2[i * 3 + 1] = displayY;
        positions2[i * 3 + 2] = displayZ;
        colors2[i * 3] = r;
        colors2[i * 3 + 1] = g;
        colors2[i * 3 + 2] = b;
        pointCount2++;
        
        // 每次都更新点云显示
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
    
    // 场景 - 使用浅色背景
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f4f8);  // 浅灰蓝色背景
    // 不使用雾效果，保持清晰
    
    // 相机 - 调整位置以查看更大的设备
    camera = new THREE.PerspectiveCamera(
        40,
        container.clientWidth / container.clientHeight,
        1,
        20000  // 增加远裁切面
    );
    camera.position.set(1200, 800, 1500);  // 拉远相机
    
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
    
    // 灯光系统 - 增强亮度
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);  // 增强环境光
    scene.add(ambientLight);
    
    const mainLight = new THREE.DirectionalLight(0xffffff, 1.5);  // 增强主光
    mainLight.position.set(500, 800, 500);
    mainLight.castShadow = true;
    scene.add(mainLight);
    
    // 添加填充光
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.8);
    fillLight.position.set(-500, 300, -500);
    scene.add(fillLight);
    
    const bottomLight = new THREE.PointLight(0xffffff, 0.5);  // 改为白色
    bottomLight.position.set(0, -200, 0);
    scene.add(bottomLight);
    
    // 网格 - 浅色背景上使用深色网格
    const gridHelper = new THREE.GridHelper(4000, 40, 0x888888, 0xcccccc);
    gridHelper.position.y = -300;
    scene.add(gridHelper);
    
    // 创建旋转组（模具和探头轨迹）
    rotatingGroup = new THREE.Group();
    scene.add(rotatingGroup);
    
    // 创建完整设备模型
    createMachineModel();
    
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
    // 材质库 - 使用更鲜明的颜色
    const materials = {
        framePaint: new THREE.MeshStandardMaterial({ color: 0x2563eb, roughness: 0.5, metalness: 0.3 }),  // 蓝色机架
        steelShiny: new THREE.MeshStandardMaterial({ color: 0xc0c0c0, roughness: 0.2, metalness: 0.9 }),  // 亮银色
        steelMatte: new THREE.MeshStandardMaterial({ color: 0x808080, roughness: 0.5, metalness: 0.7 }),  // 哑光银
        railBlack: new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.4, metalness: 0.3 }),   // 深灰色导轨
        anodizedBlack: new THREE.MeshStandardMaterial({ color: 0x1a1a2e, roughness: 0.5, metalness: 0.5 }),
        probeBody: new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.2, metalness: 0.1 }),
        indicatorTip: new THREE.MeshStandardMaterial({ color: 0xff3333, emissive: 0xff0000, emissiveIntensity: 0.3 }),
        probe1Color: new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.3, metalness: 0.5 }), // 鲜绿色
        probe2Color: new THREE.MeshStandardMaterial({ color: 0x3b82f6, roughness: 0.3, metalness: 0.5 })  // 鲜蓝色
    };
    
    // 机架组
    const machineGroup = new THREE.Group();
    scene.add(machineGroup);
    
    // 1. 机架 (Frame) - 加大以适应更长的导轨
    const frameGroup = new THREE.Group();
    const frameWidth = 1700, frameHeight = 450;  // 加宽机架
    
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
    // 主轴 - 加长以匹配导轨
    const mainShaft = new THREE.Mesh(
        new THREE.CylinderGeometry(35, 35, 1400, 32),
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
    leftShaft.position.x = -750;
    rotatingGroup.add(leftShaft);
    
    // 右侧轴
    const rightShaft = new THREE.Mesh(
        new THREE.CylinderGeometry(25, 25, 150, 32),
        materials.steelShiny
    );
    rightShaft.rotation.z = Math.PI / 2;
    rightShaft.position.x = 775;
    rotatingGroup.add(rightShaft);
    
    // 轴承座
    const bearingL = new THREE.Mesh(
        new THREE.BoxGeometry(50, 80, 80),
        materials.steelMatte
    );
    bearingL.position.x = -800;
    machineGroup.add(bearingL);
    
    const bearingR = new THREE.Mesh(
        new THREE.BoxGeometry(50, 80, 80),
        materials.steelMatte
    );
    bearingR.position.x = 800;
    machineGroup.add(bearingR);
    
    // 电机联轴器
    const motorCoupling = new THREE.Mesh(
        new THREE.CylinderGeometry(30, 30, 60, 32),
        materials.framePaint
    );
    motorCoupling.rotation.z = Math.PI / 2;
    motorCoupling.position.x = 850;
    machineGroup.add(motorCoupling);
    
    // 伺服电机
    const servoMotor = new THREE.Mesh(
        new THREE.BoxGeometry(80, 80, 120),
        materials.anodizedBlack
    );
    servoMotor.position.x = 930;
    machineGroup.add(servoMotor);
    
    // 3. 导轨系统 - 加长以适应实际行程(-700 ~ +700mm)
    const railLength = 1500;  // 加长导轨
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
            camera.position.set(0, 0, 2000);  // 增加距离
            controls.target.set(0, 0, 0);
            break;
        case 'top':
            camera.position.set(0, 2000, 0);  // 增加距离
            controls.target.set(0, 0, 0);
            break;
        case 'side':
            camera.position.set(2000, 0, 0);  // 增加距离
            controls.target.set(0, 0, 0);
            break;
        case 'iso':
            camera.position.set(1200, 800, 1500);  // 增加距离
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

// ============== 理论点云加载 ==============
document.getElementById('loadTheoreticalBtn').addEventListener('click', async () => {
    if (!ws || !isConnected) {
        alert('请先连接 PLC 后再加载理论点云');
        return;
    }
    
    try {
        // 通过 Electron API 打开文件选择对话框
        const result = await window.electronAPI.selectTheoreticalFile();
        
        if (!result.success) {
            console.log('用户取消选择文件');
            return;
        }
        
        const filePath = result.filePath;
        console.log('选择的理论点云文件:', filePath);
        
        // 更新 UI 状态
        document.getElementById('theoreticalFileName').textContent = '⏳ 加载中...';
        document.getElementById('theoreticalPointCount').textContent = '';
        
        // 发送加载请求到 WebSocket 服务器
        ws.send(JSON.stringify({
            cmd: 'load_theoretical',
            filePath: filePath
        }));
        
    } catch (error) {
        console.error('加载理论点云失败:', error);
        document.getElementById('theoreticalFileName').textContent = `❌ 加载失败: ${error.message}`;
    }
});
// ============== 手动操作功能 ==============

// 点动控制（按住按钮时持续发送）
let activeJog = {}; // 存储当前激活的点动状态 {axis: {direction, coilAddr, startTime}}

// 全局mouseup事件（防止鼠标在按钮外释放）
document.addEventListener('mouseup', () => {
    Object.keys(activeJog).forEach(axis => {
        stopJog(parseInt(axis));
    });
});

document.querySelectorAll('.jog-btn').forEach(btn => {
    const axis = parseInt(btn.dataset.axis);
    const dir = btn.dataset.dir;
    
    // 防止默认行为和文本选择
    btn.addEventListener('selectstart', (e) => e.preventDefault());
    btn.addEventListener('dragstart', (e) => e.preventDefault());
    
    // 鼠标按下开始点动
    btn.addEventListener('mousedown', (e) => {
        e.preventDefault();
        e.stopPropagation();
        startJog(axis, dir);
    });
    
    btn.addEventListener('mouseup', (e) => {
        e.preventDefault();
        e.stopPropagation();
        stopJog(axis);
    });
    
    // 只在真正离开按钮且按钮未按下时才停止
    btn.addEventListener('mouseleave', (e) => {
        // 检查鼠标按键状态，如果还在按下就不停止
        if (e.buttons === 0 && activeJog[axis]) {
            stopJog(axis);
        }
    });
    
    // 触摸支持
    btn.addEventListener('touchstart', (e) => { 
        e.preventDefault(); 
        startJog(axis, dir); 
    });
    btn.addEventListener('touchend', (e) => { 
        e.preventDefault(); 
        stopJog(axis); 
    });
});

function startJog(axis, direction) {
    if (!ws || !isConnected) {
        console.warn('未连接到 PLC');
        return;
    }
    
    // 如果这个轴已经在点动同一方向，忽略重复请求
    if (activeJog[axis] && activeJog[axis].direction === direction) {
        console.log(`轴${axis}已在点动${direction}，忽略重复请求`);
        return;
    }
    
    // 如果这个轴在点动相反方向，先停止
    if (activeJog[axis] && activeJog[axis].direction !== direction) {
        const oldCoilAddr = activeJog[axis].coilAddr;
        ws.send(JSON.stringify({
            cmd: 'write_coil',
            address: oldCoilAddr,
            value: false
        }));
        delete activeJog[axis];
        // 短暂延迟后启动新方向
        setTimeout(() => startJog(axis, direction), 100);
        return;
    }
    
    // 映射轴ID到线圈地址
    const axisMap = {
        1: { forward: 1000, backward: 1001, speedAddr: 41188 }, // 1#X轴
        2: { forward: 1100, backward: 1101, speedAddr: 41288 }, // 2#X轴
        3: { forward: 1200, backward: 1201, speedAddr: null }   // 旋转轴（无速度设置）
    };
    
    const config = axisMap[axis];
    if (!config) return;
    
    const coilAddr = direction === 'forward' ? config.forward : config.backward;
    
    // 立即标记为激活状态（防止mouseup过早触发）
    activeJog[axis] = { 
        direction, 
        coilAddr,
        startTime: Date.now()
    };
    
    // 获取点动速度（单位：mm 或 °）
    let speed = 20; // 默认速度
    if (axis === 1) speed = parseInt(document.getElementById('x1JogSpeed').value) || 20;
    else if (axis === 2) speed = parseInt(document.getElementById('x2JogSpeed').value) || 20;
    else if (axis === 3) speed = parseInt(document.getElementById('rotJogSpeed').value) || 5;
    
    // 转换为PLC内部值（可能需要精度缩放）
    // X轴速度：mm → 0.01mm单位，所以乘以100
    // 旋转轴：度 → 0.01度单位，所以乘以100
    const speedValue = speed * 100;
    
    // 1. 先设置速度（如果有速度寄存器）
    if (config.speedAddr) {
        ws.send(JSON.stringify({
            cmd: 'write_register',
            address: config.speedAddr,
            value: speedValue
        }));
        
        // 2. 延迟50ms后发送点动命令（确保速度先被PLC接收）
        setTimeout(() => {
            ws.send(JSON.stringify({
                cmd: 'write_coil',
                address: coilAddr,
                value: true
            }));
            console.log(`✅ 开始点动: 轴${axis}, 方向=${direction}, 速度=${speed}mm (PLC值=${speedValue}), 地址=${coilAddr}`);
        }, 50);
    } else {
        // 旋转轴没有速度寄存器，直接发送点动命令
        ws.send(JSON.stringify({
            cmd: 'write_coil',
            address: coilAddr,
            value: true
        }));
        console.log(`✅ 开始点动: 轴${axis}, 方向=${direction}, 速度=${speed}°, 地址=${coilAddr}`);
    }
}

function stopJog(axis) {
    if (!ws || !isConnected) return;
    if (!activeJog[axis]) return; // 如果没有激活的点动，直接返回
    
    const { coilAddr, startTime } = activeJog[axis];
    
    // 最小持续时间保护：确保点动至少持续300ms（真机需要更长时间）
    const MIN_JOG_DURATION = 300; // ms
    const elapsed = Date.now() - startTime;
    
    if (elapsed < MIN_JOG_DURATION) {
        const delay = MIN_JOG_DURATION - elapsed;
        console.log(`⏱ 点动持续时间不足${MIN_JOG_DURATION}ms，延迟${delay}ms后停止`);
        setTimeout(() => stopJog(axis), delay);
        return;
    }
    
    // 只停止当前激活的方向
    ws.send(JSON.stringify({
        cmd: 'write_coil',
        address: coilAddr,
        value: false
    }));
    
    console.log(`⏹ 停止点动: 轴${axis}, 地址=${coilAddr}, 持续${elapsed}ms`);
    delete activeJog[axis];
}

// 回原点（初始化）
function homeAxis(axis) {
    if (!ws || !isConnected) {
        alert('未连接到 PLC');
        return;
    }
    
    const axisMap = {
        1: { coil: 1002, name: '1#X轴' },
        2: { coil: 1102, name: '2#X轴' },
        3: { coil: 1202, name: '旋转轴' }
    };
    
    const config = axisMap[axis];
    if (!config) return;
    
    if (confirm(`确定要${config.name}回原点吗？`)) {
        ws.send(JSON.stringify({
            cmd: 'write_coil',
            address: config.coil,
            value: true
        }));
        console.log(`${config.name}回原点`);
    }
}

// 定位动作（移动到指定位置）
function moveToPosition(axis) {
    if (!ws || !isConnected) {
        alert('未连接到 PLC');
        return;
    }
    
    const axisMap = {
        1: { 
            targetAddr: 41212, 
            speedAddr: 41190, 
            actionCoil: 1010,
            posInput: 'x1TargetPos',
            name: '1#X轴',
            scale: 100 // 0.01mm 精度
        },
        2: { 
            targetAddr: 41312, 
            speedAddr: 41290, 
            actionCoil: 1110,
            posInput: 'x2TargetPos',
            name: '2#X轴',
            scale: 100
        },
        3: { 
            targetAddr: 41412, 
            speedAddr: 41390, 
            actionCoil: 1210,
            posInput: 'rotTargetPos',
            name: '旋转轴',
            scale: 100 // 0.01度 精度
        }
    };
    
    const config = axisMap[axis];
    if (!config) return;
    
    // 获取目标位置
    const targetPos = parseFloat(document.getElementById(config.posInput).value);
    if (isNaN(targetPos)) {
        alert('请输入有效的目标位置');
        return;
    }
    
    // 转换为整数（根据精度）
    const targetValue = Math.round(targetPos * config.scale);
    
    // 获取动作速度（从前端输入框读取）
    let speed = 40;
    const speedInputId = axis === 1 ? 'x1ActionSpeed' : axis === 2 ? 'x2ActionSpeed' : 'rotActionSpeed';
    const speedInput = document.getElementById(speedInputId);
    
    if (speedInput) {
        speed = parseInt(speedInput.value) || 40;
        console.log(`读取到速度输入框 ${speedInputId} = ${speedInput.value}`);
    } else {
        console.warn(`未找到速度输入框: ${speedInputId}，使用默认速度 ${speed}`);
    }
    
    // 转换为PLC内部值（0.01mm/0.01度精度，乘以100）
    const speedValue = speed * 100;
    
    console.log(`定位动作: ${config.name}, 目标=${targetPos}, 速度=${speed}mm/s (PLC值=${speedValue})`);
    
    // 按顺序发送命令，确保PLC正确接收
    // 1. 先设置动作速度
    ws.send(JSON.stringify({
        cmd: 'write_register',
        address: config.speedAddr,
        value: speedValue
    }));
    
    // 2. 延迟50ms后设置目标位置
    setTimeout(() => {
        ws.send(JSON.stringify({
            cmd: 'write_register',
            address: config.targetAddr,
            value: targetValue
        }));
        
        // 3. 先复位动作线圈（写False），确保产生上升沿
        setTimeout(() => {
            ws.send(JSON.stringify({
                cmd: 'write_coil',
                address: config.actionCoil,
                value: false
            }));
            
            // 4. 再延迟50ms后触发动作（写True）
            setTimeout(() => {
                ws.send(JSON.stringify({
                    cmd: 'write_coil',
                    address: config.actionCoil,
                    value: true
                }));
                console.log(`✅ 定位命令已发送: ${config.name} -> ${targetPos}`);
            }, 50);
        }, 50);
    }, 50);
}

// 整机初始化
function initializeAll() {
    if (!ws || !isConnected) {
        alert('未连接到 PLC');
        return;
    }
    
    if (confirm('确定要进行整机初始化吗？所有轴将回到原点。')) {
        ws.send(JSON.stringify({
            cmd: 'write_coil',
            address: 104, // 整机初始化线圈
            value: true
        }));
        console.log('整机初始化');
    }
}

// 更新手动操作界面的位置显示
function updateManualPositionDisplay(x1, x2, rot) {
    document.getElementById('x1ManualPos').textContent = x1.toFixed(2);
    document.getElementById('x2ManualPos').textContent = x2.toFixed(2);
    document.getElementById('rotManualPos').textContent = rot.toFixed(1);
}

// ============== IP地址历史记录管理 ==============

/**
 * 加载IP历史记录并显示快速选择按钮
 */
function loadIPHistory() {
    try {
        const historyJson = localStorage.getItem(IP_HISTORY_KEY);
        if (!historyJson) return;
        
        const history = JSON.parse(historyJson);
        if (!Array.isArray(history) || history.length === 0) return;
        
        const container = document.getElementById('ipHistoryContainer');
        const buttonsDiv = document.getElementById('ipHistoryButtons');
        
        if (!container || !buttonsDiv) return;
        
        buttonsDiv.innerHTML = '';
        
        history.forEach(ip => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-secondary text-xs py-1 px-3';
            btn.textContent = ip === '127.0.0.1' ? '🖥️ 本地仿真' : `🔗 ${ip}`;
            btn.onclick = () => selectIPFromHistory(ip);
            buttonsDiv.appendChild(btn);
        });
        
        container.classList.remove('hidden');
        console.log('已加载IP历史记录:', history);
    } catch (e) {
        console.error('加载IP历史记录失败:', e);
    }
}

/**
 * 从历史记录选择IP
 */
function selectIPFromHistory(ip) {
    const input = document.getElementById('plcIpInput');
    if (input) {
        input.value = ip;
        input.style.borderColor = '#3b82f6';
        setTimeout(() => { input.style.borderColor = ''; }, 300);
        console.log('已选择历史IP:', ip);
    }
}

/**
 * 保存IP到历史记录
 */
function saveIPToHistory(ip) {
    try {
        if (!ip || typeof ip !== 'string') return;
        
        let history = [];
        const historyJson = localStorage.getItem(IP_HISTORY_KEY);
        if (historyJson) {
            history = JSON.parse(historyJson);
            if (!Array.isArray(history)) history = [];
        }
        
        history = history.filter(item => item !== ip);
        history.unshift(ip);
        
        if (history.length > MAX_IP_HISTORY) {
            history = history.slice(0, MAX_IP_HISTORY);
        }
        
        localStorage.setItem(IP_HISTORY_KEY, JSON.stringify(history));
        console.log('IP历史记录已更新:', history);
        
        loadIPHistory();
    } catch (e) {
        console.error('保存IP历史记录失败:', e);
    }
}

// 页面加载时加载IP历史
if (document.getElementById('ipHistoryContainer')) {
    loadIPHistory();
}