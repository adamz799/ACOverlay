"""
自定义UI组件
"""

import math
from collections import deque
from typing import List

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QLinearGradient
from PyQt6.QtWidgets import QWidget


class InputTraceWidget(QWidget):
    """油门刹车转向历史曲线图"""
    
    def __init__(self, parent=None, max_samples=200):
        super().__init__(parent)
        self.max_samples = max_samples
        self.throttle_history: deque = deque(maxlen=max_samples)
        self.brake_history: deque = deque(maxlen=max_samples)
        self.steering_history: deque = deque(maxlen=max_samples)
        self.setMinimumSize(350, 100)
        
        # 颜色配置
        self.throttle_color = QColor(0, 255, 0)      # 绿色-油门
        self.brake_color = QColor(255, 50, 50)       # 红色-刹车
        self.steering_color = QColor(150, 150, 150)  # 灰色-转向
        self.bg_color = QColor(20, 20, 20, 200)      # 半透明背景
        self.grid_color = QColor(60, 60, 60)         # 网格颜色
        
        # 转向最大角度（度），用于归一化
        self.max_steering_angle = 450.0
        
    def add_data(self, throttle: float, brake: float, steering: float = 0.0):
        """添加新数据点
        
        Args:
            throttle: 油门 0-1
            brake: 刹车 0-1
            steering: 转向角度（度），负值左转，正值右转
        """
        self.throttle_history.append(throttle)
        self.brake_history.append(brake)
        # 将转向角度归一化到 -1 到 1 范围
        normalized_steering = max(-1.0, min(1.0, steering / self.max_steering_angle))
        self.steering_history.append(normalized_steering)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        # 绘制背景
        painter.fillRect(rect, self.bg_color)
        
        # 绘制网格线
        painter.setPen(QPen(self.grid_color, 1))
        for i in range(1, 4):
            y = int(rect.height() * i / 4)
            painter.drawLine(0, y, rect.width(), y)
        
        # 先绘制转向曲线（在底层）
        if len(self.steering_history) > 1:
            self._draw_steering_curve(painter, list(self.steering_history))
        
        # 再绘制油门刹车曲线（在上层）
        if len(self.throttle_history) > 1:
            self._draw_curve(painter, list(self.throttle_history), self.throttle_color)
        if len(self.brake_history) > 1:
            self._draw_curve(painter, list(self.brake_history), self.brake_color)
    
    def _draw_steering_curve(self, painter: QPainter, data: List[float]):
        """绘制转向曲线 - 中间为0，向上为左转，向下为右转"""
        if len(data) < 2:
            return
            
        path = QPainterPath()
        rect = self.rect()
        center_y = rect.height() / 2  # 中线位置
        
        x_step = rect.width() / self.max_samples
        start_x = rect.width() - len(data) * x_step
        
        # 起始点：steering为负（左转）时向上，为正（右转）时向下
        # data已归一化到 -1 到 1，乘以半高度得到偏移
        y = center_y - data[0] * (rect.height() / 2)
        path.moveTo(start_x, y)
        
        for i, value in enumerate(data[1:], 1):
            x = start_x + i * x_step
            y = center_y - value * (rect.height() / 2)
            path.lineTo(x, y)
        
        # 绘制曲线（无填充，仅线条）
        painter.setPen(QPen(self.steering_color, 2))
        painter.drawPath(path)
        
        # 绘制中线参考（转向为0的位置）
        painter.setPen(QPen(QColor(80, 80, 80), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, int(center_y), rect.width(), int(center_y))
            
    def _draw_curve(self, painter: QPainter, data: List[float], color: QColor):
        """绘制曲线"""
        if len(data) < 2:
            return
            
        path = QPainterPath()
        rect = self.rect()
        
        x_step = rect.width() / self.max_samples
        
        # 起始点
        start_x = rect.width() - len(data) * x_step
        path.moveTo(start_x, rect.height() - data[0] * rect.height())
        
        for i, value in enumerate(data[1:], 1):
            x = start_x + i * x_step
            y = rect.height() - value * rect.height()
            path.lineTo(x, y)
        
        # 绘制填充区域
        fill_path = QPainterPath(path)
        fill_path.lineTo(rect.width(), rect.height())
        fill_path.lineTo(start_x, rect.height())
        fill_path.closeSubpath()
        
        fill_color = QColor(color)
        fill_color.setAlpha(50)
        painter.fillPath(fill_path, fill_color)
        
        # 绘制曲线
        painter.setPen(QPen(color, 2))
        painter.drawPath(path)


class PedalBarWidget(QWidget):
    """油门刹车垂直条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.throttle = 0.0
        self.brake = 0.0
        self.setMinimumSize(60, 100)
        
    def set_values(self, throttle: float, brake: float):
        self.throttle = max(0, min(1, throttle))
        self.brake = max(0, min(1, brake))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        bar_width = 20
        spacing = 8
        total_width = bar_width * 2 + spacing
        start_x = (rect.width() - total_width) // 2
        
        # 背景
        bg_color = QColor(40, 40, 40, 180)
        
        # 刹车条 (左)
        brake_rect = QRectF(start_x, 10, bar_width, rect.height() - 20)
        painter.fillRect(brake_rect, bg_color)
        
        brake_fill_height = brake_rect.height() * self.brake
        brake_fill_rect = QRectF(
            brake_rect.x(), 
            brake_rect.bottom() - brake_fill_height,
            bar_width, 
            brake_fill_height
        )
        painter.fillRect(brake_fill_rect, QColor(255, 50, 50))
        
        # 油门条 (右)
        throttle_rect = QRectF(start_x + bar_width + spacing, 10, bar_width, rect.height() - 20)
        painter.fillRect(throttle_rect, bg_color)
        
        throttle_fill_height = throttle_rect.height() * self.throttle
        throttle_fill_rect = QRectF(
            throttle_rect.x(),
            throttle_rect.bottom() - throttle_fill_height,
            bar_width,
            throttle_fill_height
        )
        painter.fillRect(throttle_fill_rect, QColor(0, 255, 0))
        
        # 边框
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(brake_rect)
        painter.drawRect(throttle_rect)


class GearSpeedWidget(QWidget):
    """挡位和速度显示"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gear = 0
        self.speed = 0
        self.setMinimumSize(100, 100)
        
    def set_values(self, gear: int, speed: float):
        self.gear = gear
        self.speed = int(speed)
        self.update()
        
    def get_gear_text(self) -> str:
        """获取挡位文本"""
        if self.gear == 0:
            return "R"
        elif self.gear == 1:
            return "N"
        else:
            return str(self.gear - 1)
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        # 背景
        painter.fillRect(rect, QColor(30, 30, 30, 200))
        
        # 挡位 - 大字体居中
        gear_font = QFont("Arial", 48, QFont.Weight.Bold)
        painter.setFont(gear_font)
        painter.setPen(QColor(255, 255, 255))
        
        gear_text = self.get_gear_text()
        gear_rect = QRectF(0, 5, rect.width(), rect.height() * 0.6)
        painter.drawText(gear_rect, Qt.AlignmentFlag.AlignCenter, gear_text)
        
        # 速度 - 底部
        speed_font = QFont("Arial", 18, QFont.Weight.Bold)
        painter.setFont(speed_font)
        painter.setPen(QColor(200, 200, 200))
        
        speed_text = f"{self.speed}"
        speed_rect = QRectF(0, rect.height() * 0.55, rect.width(), rect.height() * 0.25)
        painter.drawText(speed_rect, Qt.AlignmentFlag.AlignCenter, speed_text)
        
        # 单位
        unit_font = QFont("Arial", 10)
        painter.setFont(unit_font)
        painter.setPen(QColor(150, 150, 150))
        unit_rect = QRectF(0, rect.height() * 0.78, rect.width(), rect.height() * 0.2)
        painter.drawText(unit_rect, Qt.AlignmentFlag.AlignCenter, "km/h")


class GForceWidget(QWidget):
    """G力显示点阵"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.g_lateral = 0.0
        self.g_longitudinal = 0.0
        self.max_g = 3.0  # 最大显示G值
        self.setMinimumSize(120, 120)  # 加大尺寸以容纳数值显示
        
    def set_values(self, g_lateral: float, g_longitudinal: float):
        self.g_lateral = g_lateral
        self.g_longitudinal = g_longitudinal
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center_x = rect.width() / 2
        center_y = rect.height() / 2
        # 留出空间给数值显示
        radius = min(rect.width(), rect.height()) / 2 - 18
        
        # 背景圆
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.setBrush(QBrush(QColor(30, 30, 30, 200)))
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)
        
        # 十字线
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawLine(int(center_x - radius), int(center_y), 
                        int(center_x + radius), int(center_y))
        painter.drawLine(int(center_x), int(center_y - radius), 
                        int(center_x), int(center_y + radius))
        
        # 圆环
        for r in [radius * 0.33, radius * 0.66]:
            painter.drawEllipse(QPointF(center_x, center_y), r, r)
        
        # G力点
        g_x = self.g_lateral / self.max_g * radius
        g_y = -self.g_longitudinal / self.max_g * radius  # Y轴反转
        
        # 限制在圆内
        dist = math.sqrt(g_x**2 + g_y**2)
        if dist > radius:
            scale = radius / dist
            g_x *= scale
            g_y *= scale
        
        # 根据G值设置颜色
        total_g = math.sqrt(self.g_lateral**2 + self.g_longitudinal**2)
        if total_g < 1.0:
            dot_color = QColor(0, 255, 0)  # 绿色
        elif total_g < 2.0:
            dot_color = QColor(255, 255, 0)  # 黄色
        else:
            dot_color = QColor(255, 50, 50)  # 红色
            
        painter.setBrush(QBrush(dot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center_x + g_x, center_y + g_y), 6, 6)
        
        # 绘制G值数值
        value_font = QFont("Arial", 9, QFont.Weight.Bold)
        painter.setFont(value_font)
        painter.setPen(QColor(200, 200, 200))
        
        # 横向G值 (显示在右侧)
        lat_text = f"{abs(self.g_lateral):.1f}G"
        lat_color = QColor(255, 200, 100) if self.g_lateral >= 0 else QColor(100, 200, 255)
        painter.setPen(lat_color)
        lat_rect = QRectF(center_x + radius + 2, center_y - 8, 30, 16)
        painter.drawText(lat_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, lat_text)
        
        # 纵向G值 (显示在底部)
        long_text = f"{abs(self.g_longitudinal):.1f}G"
        long_color = QColor(0, 255, 100) if self.g_longitudinal >= 0 else QColor(255, 100, 100)
        painter.setPen(long_color)
        long_rect = QRectF(center_x - 20, center_y + radius + 2, 40, 14)
        painter.drawText(long_rect, Qt.AlignmentFlag.AlignCenter, long_text)
        
        # 合成G值 (显示在左上角)
        painter.setPen(QColor(255, 255, 255))
        total_text = f"{total_g:.1f}G"
        total_rect = QRectF(2, 2, 40, 14)
        painter.drawText(total_rect, Qt.AlignmentFlag.AlignLeft, total_text)


class SteeringWheelWidget(QWidget):
    """方向盘显示"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0.0  # 弧度
        self.max_rotation = 450  # 最大旋转角度(度)
        self.setMinimumSize(80, 80)
        
    def set_angle(self, angle_rad: float):
        """设置角度（弧度）"""
        self.angle = angle_rad
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center_x = rect.width() / 2
        center_y = rect.height() / 2
        radius = min(rect.width(), rect.height()) / 2 - 8
        
        # 保存状态并旋转
        painter.save()
        painter.translate(center_x, center_y)
        
        # 转换弧度为度数，并应用旋转
        rotation_deg = math.degrees(self.angle)
        painter.rotate(rotation_deg)
        
        # 方向盘外圈
        painter.setPen(QPen(QColor(200, 200, 200), 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(0, 0), radius, radius)
        
        # 方向盘辐条
        painter.setPen(QPen(QColor(180, 180, 180), 3))
        # 上方辐条
        painter.drawLine(QPointF(0, -radius * 0.3), QPointF(0, -radius))
        # 左下辐条
        painter.drawLine(QPointF(-radius * 0.3, radius * 0.15), 
                        QPointF(-radius * 0.85, radius * 0.5))
        # 右下辐条
        painter.drawLine(QPointF(radius * 0.3, radius * 0.15), 
                        QPointF(radius * 0.85, radius * 0.5))
        
        # 中心
        painter.setBrush(QBrush(QColor(60, 60, 60)))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawEllipse(QPointF(0, 0), radius * 0.25, radius * 0.25)
        
        # 顶部标记（12点位置）
        painter.setBrush(QBrush(QColor(255, 200, 0)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(QRectF(-3, -radius - 2, 6, 6))
        
        painter.restore()


class RPMLightsWidget(QWidget):
    """转速指示灯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rpm = 0
        self.max_rpm = 8000
        self.setMinimumSize(80, 20)
        
    def set_values(self, rpm: int, max_rpm: int = 8000):
        self.rpm = rpm
        self.max_rpm = max_rpm
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        num_lights = 6
        light_size = 10
        spacing = 4
        total_width = num_lights * light_size + (num_lights - 1) * spacing
        start_x = (rect.width() - total_width) / 2
        center_y = rect.height() / 2
        
        rpm_ratio = self.rpm / self.max_rpm if self.max_rpm > 0 else 0
        lights_on = int(rpm_ratio * num_lights)
        
        for i in range(num_lights):
            x = start_x + i * (light_size + spacing)
            
            # 确定颜色
            if i < 2:
                on_color = QColor(0, 255, 0)  # 绿色
            elif i < 4:
                on_color = QColor(255, 200, 0)  # 黄色
            else:
                on_color = QColor(255, 50, 50)  # 红色
                
            if i < lights_on:
                painter.setBrush(QBrush(on_color))
            else:
                dim_color = QColor(on_color)
                dim_color.setAlpha(40)
                painter.setBrush(QBrush(dim_color))
                
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x + light_size/2, center_y), 
                               light_size/2, light_size/2)
