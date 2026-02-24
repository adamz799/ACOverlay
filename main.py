"""
AC Overlay 主窗口
神力科莎遥测数据实时显示插件
"""

import sys
import os
import math
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QAction, QIcon, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, 
    QVBoxLayout, QSystemTrayIcon, QMenu, QLabel
)

from widgets import (
    InputTraceWidget, PedalBarWidget, GearSpeedWidget,
    GForceWidget, SteeringWheelWidget, RPMLightsWidget
)
from ac_reader import ACSharedMemory, TelemetryData
from telemetry_logger import TelemetryLogger, SessionInfo


class OverlayWindow(QMainWindow):
    """主Overlay窗口"""
    
    def __init__(self):
        super().__init__()
        
        # AC共享内存读取器
        self.ac_reader = ACSharedMemory()
        
        # 遥测日志记录器
        self.logger = TelemetryLogger(output_dir="logs")
        
        # 录制采样控制
        self._last_record_time = 0.0
        
        # 状态
        self.is_visible = True
        self.auto_hide_enabled = True
        self.manual_override = False  # 手动控制覆盖自动
        self.was_driving = False
        self.auto_record_enabled = True  # 自动录制开关
        
        # 拖动支持
        self._drag_pos = None
        
        self.init_ui()
        self.init_tray()
        self.init_hotkeys()
        self.init_timer()
        
    def init_ui(self):
        """初始化UI"""
        # 窗口设置 - 无边框、置顶、透明背景
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # 不在任务栏显示
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 窗口大小和位置
        self.setFixedSize(900, 160)
        self.center_on_screen_bottom()
        
        # 中央部件
        central = QWidget()
        central.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 20, 180);
                border-radius: 8px;
            }
        """)
        self.setCentralWidget(central)
        
        # 主布局
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # 1. 输入曲线图（左侧）
        self.input_trace = InputTraceWidget()
        self.input_trace.setFixedSize(300, 130)
        main_layout.addWidget(self.input_trace)
        
        # 2. 油门刹车条
        self.pedal_bars = PedalBarWidget()
        self.pedal_bars.setFixedSize(60, 130)
        main_layout.addWidget(self.pedal_bars)
        
        # 3. 中间区域 - RPM灯 + 挡位速度
        middle_layout = QVBoxLayout()
        middle_layout.setSpacing(5)
        
        self.rpm_lights = RPMLightsWidget()
        self.rpm_lights.setFixedSize(100, 25)
        middle_layout.addWidget(self.rpm_lights, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.gear_speed = GearSpeedWidget()
        self.gear_speed.setFixedSize(100, 100)
        middle_layout.addWidget(self.gear_speed, alignment=Qt.AlignmentFlag.AlignCenter)
        
        main_layout.addLayout(middle_layout)
        
        # 4. G力显示（加大以显示数值）
        self.g_force = GForceWidget()
        self.g_force.setFixedSize(130, 130)
        main_layout.addWidget(self.g_force, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 5. 方向盘
        self.steering = SteeringWheelWidget()
        self.steering.setFixedSize(110, 110)
        main_layout.addWidget(self.steering, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 6. 状态指示区域
        status_layout = QVBoxLayout()
        status_layout.setSpacing(2)
        
        # 连接状态
        self.status_label = QLabel("●")
        self.status_label.setStyleSheet("color: red; font-size: 16px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setToolTip("连接状态")
        status_layout.addWidget(self.status_label)
        
        # 录制状态
        self.record_label = QLabel("○")
        self.record_label.setStyleSheet("color: #666666; font-size: 14px;")
        self.record_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.record_label.setToolTip("录制状态 (F11)")
        status_layout.addWidget(self.record_label)
        
        status_layout.addStretch()
        main_layout.addLayout(status_layout)
        
    def center_on_screen_bottom(self):
        """将窗口居中放置在屏幕底部"""
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 50  # 距离底部50px
        self.move(x, y)
        
    def init_tray(self):
        """初始化系统托盘"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 显示/隐藏动作
        self.toggle_action = QAction("隐藏 (F9)", self)
        self.toggle_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(self.toggle_action)
        
        # 自动隐藏开关
        self.auto_hide_action = QAction("自动显隐", self)
        self.auto_hide_action.setCheckable(True)
        self.auto_hide_action.setChecked(True)
        self.auto_hide_action.triggered.connect(self.toggle_auto_hide)
        tray_menu.addAction(self.auto_hide_action)
        
        tray_menu.addSeparator()
        
        # === 录制相关菜单 ===
        # 开始/停止录制
        self.record_action = QAction("开始录制 (F11)", self)
        self.record_action.triggered.connect(self.toggle_recording)
        tray_menu.addAction(self.record_action)
        
        # 自动录制开关
        self.auto_record_action = QAction("自动录制", self)
        self.auto_record_action.setCheckable(True)
        self.auto_record_action.setChecked(True)
        self.auto_record_action.triggered.connect(self.toggle_auto_record)
        self.auto_record_action.setToolTip("驾驶时自动开始录制")
        tray_menu.addAction(self.auto_record_action)
        
        # 打开日志文件夹
        open_logs_action = QAction("打开日志文件夹", self)
        open_logs_action.triggered.connect(self.open_logs_folder)
        tray_menu.addAction(open_logs_action)
        
        tray_menu.addSeparator()
        
        # 退出动作
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("AC Overlay - 按F9切换显示, F11录制")
        
        # 设置图标（使用默认图标）
        self.tray_icon.setIcon(self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon
        ))
        
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_activated)
        
    def init_hotkeys(self):
        """初始化全局热键"""
        try:
            import keyboard
            keyboard.add_hotkey('F9', self.toggle_visibility_hotkey)
            keyboard.add_hotkey('F10', self.toggle_auto_hide_hotkey)
            keyboard.add_hotkey('F11', self.toggle_recording_hotkey)
            keyboard.add_hotkey('F12', self.toggle_auto_record_hotkey)
        except Exception as e:
            print(f"热键注册失败: {e}")
            
    def init_timer(self):
        """初始化更新定时器"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_telemetry)
        self.update_timer.start(16)  # ~60 FPS
        
    def update_telemetry(self):
        """更新遥测数据"""
        data = self.ac_reader.get_telemetry()
        
        # 更新连接状态
        if data.is_connected:
            self.status_label.setStyleSheet("color: #00ff00; font-size: 16px;")
        else:
            self.status_label.setStyleSheet("color: #ff3333; font-size: 16px;")
        
        # 更新各组件
        # 转向角度从弧度转为度数
        steering_deg = math.degrees(data.steer_angle) if hasattr(data, 'steer_angle') else 0.0
        self.input_trace.add_data(data.throttle, data.brake, steering_deg)
        self.pedal_bars.set_values(data.throttle, data.brake)
        self.gear_speed.set_values(data.gear, data.speed_kmh)
        self.rpm_lights.set_values(data.rpm)
        self.g_force.set_values(data.g_lateral, data.g_longitudinal)
        self.steering.set_angle(data.steer_angle)
        
        # === 自动录制逻辑 ===
        if self.auto_record_enabled and data.is_connected:
            if data.is_driving and not self.was_driving:
                # 开始驾驶 - 自动开始录制
                if not self.logger.is_recording:
                    self.start_recording()
            elif not data.is_driving and self.was_driving:
                # 停止驾驶 - 自动停止录制（可选，也可以不停止）
                pass  # 保持录制，直到手动停止或退出
        
        # === 录制数据（带采样率控制） ===
        if self.logger.is_recording and data.is_connected:
            import time
            current_time = time.perf_counter()
            # 采样率控制：每50ms记录一次（20Hz），而不是每帧都记录
            if current_time - self._last_record_time >= self.logger.SAMPLE_INTERVAL_MS / 1000.0:
                full_data = self.ac_reader.get_full_telemetry()
                if full_data:
                    self.logger.record(full_data)
                    self._last_record_time = current_time
                    # 更新录制指示灯（闪烁效果）
                    if self.logger.record_count % 10 < 5:
                        self.record_label.setStyleSheet("color: #ff0000; font-size: 14px;")
                    else:
                        self.record_label.setStyleSheet("color: #aa0000; font-size: 14px;")
                    self.record_label.setToolTip(
                        f"录制中: {self.logger.current_filename}\n"
                        f"记录数: {self.logger.record_count}"
                    )
        
        # 自动显隐逻辑
        if self.auto_hide_enabled and not self.manual_override:
            if data.is_driving and not self.was_driving:
                # 开始驾驶 - 显示
                self.show()
                self.is_visible = True
                self.update_toggle_action_text()
            elif not data.is_driving and self.was_driving:
                # 停止驾驶 - 隐藏（延迟处理，避免短暂停止时闪烁）
                pass  # 可以添加延迟隐藏逻辑
            
        self.was_driving = data.is_driving
            
    def start_recording(self):
        """开始录制"""
        session_info = self.ac_reader.get_session_info()
        if not session_info:
            # 未连接到游戏，使用默认信息
            session_info = SessionInfo(
                car_model="unknown",
                track="unknown",
                start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        else:
            session_info.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        filepath = self.logger.start_recording(session_info)
        self.update_record_action_text()
        
        # 更新录制指示灯
        self.record_label.setText("●")
        self.record_label.setStyleSheet("color: #ff0000; font-size: 14px;")
        
        # 托盘通知
        self.tray_icon.showMessage(
            "开始录制",
            f"正在录制遥测数据到:\n{self.logger.current_filename}",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        
    def stop_recording(self):
        """停止录制"""
        filepath = self.logger.stop_recording()
        self.update_record_action_text()
        
        # 更新录制指示灯
        self.record_label.setText("○")
        self.record_label.setStyleSheet("color: #666666; font-size: 14px;")
        self.record_label.setToolTip("录制状态 (F11)")
        
        if filepath:
            # 托盘通知
            self.tray_icon.showMessage(
                "录制完成",
                f"遥测数据已保存到:\n{os.path.basename(filepath)}\n"
                f"共 {self.logger.record_count} 条记录",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            
    def toggle_recording(self):
        """切换录制状态"""
        if self.logger.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
            
    def toggle_recording_hotkey(self):
        """热键触发的录制切换"""
        QTimer.singleShot(0, self.toggle_recording)
        
    def toggle_auto_record(self):
        """切换自动录制"""
        self.auto_record_enabled = self.auto_record_action.isChecked()
        
    def toggle_auto_record_hotkey(self):
        """热键触发的自动录制切换"""
        def do_toggle():
            self.auto_record_action.setChecked(not self.auto_record_action.isChecked())
            self.toggle_auto_record()
        QTimer.singleShot(0, do_toggle)
        
    def update_record_action_text(self):
        """更新录制菜单文字"""
        if self.logger.is_recording:
            self.record_action.setText("停止录制 (F11)")
        else:
            self.record_action.setText("开始录制 (F11)")
            
    def open_logs_folder(self):
        """打开日志文件夹"""
        logs_path = os.path.abspath(self.logger.output_dir)
        os.makedirs(logs_path, exist_ok=True)
        os.startfile(logs_path)
            
    def toggle_visibility(self):
        """切换可见性"""
        self.manual_override = True  # 手动操作时禁用自动
        if self.is_visible:
            self.hide()
            self.is_visible = False
        else:
            self.show()
            self.is_visible = True
        self.update_toggle_action_text()
        
    def toggle_visibility_hotkey(self):
        """热键触发的切换（在主线程执行）"""
        QTimer.singleShot(0, self.toggle_visibility)
        
    def toggle_auto_hide(self):
        """切换自动隐藏"""
        self.auto_hide_enabled = self.auto_hide_action.isChecked()
        if self.auto_hide_enabled:
            self.manual_override = False
            
    def toggle_auto_hide_hotkey(self):
        """热键触发的自动隐藏切换"""
        def do_toggle():
            self.auto_hide_action.setChecked(not self.auto_hide_action.isChecked())
            self.toggle_auto_hide()
        QTimer.singleShot(0, do_toggle)
        
    def update_toggle_action_text(self):
        """更新托盘菜单文字"""
        if self.is_visible:
            self.toggle_action.setText("隐藏 (F9)")
        else:
            self.toggle_action.setText("显示 (F9)")
            
    def on_tray_activated(self, reason):
        """托盘图标被点击"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_visibility()
            
    def quit_app(self):
        """退出应用"""
        # 停止录制
        if self.logger.is_recording:
            self.stop_recording()
            
        self.ac_reader.disconnect()
        try:
            import keyboard
            keyboard.unhook_all()
        except:
            pass
        QApplication.quit()
        
    # 拖动支持
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            
    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        
    def closeEvent(self, event):
        """关闭事件 - 最小化到托盘而不是退出"""
        event.ignore()
        self.hide()
        self.is_visible = False
        self.update_toggle_action_text()
        self.tray_icon.showMessage(
            "AC Overlay",
            "程序已最小化到系统托盘\n"
            "F9:显示/隐藏  F11:录制",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # 设置应用信息
    app.setApplicationName("AC Overlay")
    app.setApplicationDisplayName("Assetto Corsa Telemetry Overlay")
    
    window = OverlayWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()