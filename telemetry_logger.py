"""
遥测数据日志记录器
支持 RaceChrono 兼容的 CSV 格式
"""

import os
import csv
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class FullTelemetryData:
    """完整遥测数据记录"""
    # 时间信息
    timestamp: float = 0.0           # 相对时间（秒）
    session_time: float = 0.0        # 会话时间
    lap_number: int = 0              # 当前圈数
    lap_time_ms: int = 0             # 当前圈时间（毫秒）
    
    # 车辆输入
    throttle: float = 0.0            # 油门 0-1
    brake: float = 0.0               # 刹车 0-1
    clutch: float = 0.0              # 离合 0-1
    steering: float = 0.0            # 方向盘角度（度）
    
    # 运动状态
    speed_kmh: float = 0.0           # 速度 km/h
    speed_ms: float = 0.0            # 速度 m/s
    gear: int = 0                    # 挡位
    rpm: int = 0                     # 转速
    
    # 速度向量
    velocity_x: float = 0.0          # 速度X（m/s）
    velocity_y: float = 0.0          # 速度Y（m/s）
    velocity_z: float = 0.0          # 速度Z（m/s）
    
    # G力
    g_lateral: float = 0.0           # 横向G
    g_longitudinal: float = 0.0      # 纵向G
    g_vertical: float = 0.0          # 垂直G
    
    # 车辆姿态
    heading: float = 0.0             # 航向角（度）
    pitch: float = 0.0               # 俯仰角（度）
    roll: float = 0.0                # 横滚角（度）
    
    # 角速度
    angular_vel_x: float = 0.0
    angular_vel_y: float = 0.0
    angular_vel_z: float = 0.0
    
    # 位置
    normalized_pos: float = 0.0      # 赛道位置 0-1
    distance_traveled: float = 0.0   # 行驶距离（米）
    
    # 车辆坐标 (世界坐标)
    world_pos_x: float = 0.0
    world_pos_y: float = 0.0
    world_pos_z: float = 0.0
    
    # 轮胎数据 - 前左/前右/后左/后右
    tyre_slip_fl: float = 0.0
    tyre_slip_fr: float = 0.0
    tyre_slip_rl: float = 0.0
    tyre_slip_rr: float = 0.0
    
    tyre_load_fl: float = 0.0
    tyre_load_fr: float = 0.0
    tyre_load_rl: float = 0.0
    tyre_load_rr: float = 0.0
    
    tyre_pressure_fl: float = 0.0
    tyre_pressure_fr: float = 0.0
    tyre_pressure_rl: float = 0.0
    tyre_pressure_rr: float = 0.0
    
    tyre_temp_fl: float = 0.0        # 核心温度
    tyre_temp_fr: float = 0.0
    tyre_temp_rl: float = 0.0
    tyre_temp_rr: float = 0.0
    
    tyre_wear_fl: float = 0.0
    tyre_wear_fr: float = 0.0
    tyre_wear_rl: float = 0.0
    tyre_wear_rr: float = 0.0
    
    # 刹车温度
    brake_temp_fl: float = 0.0
    brake_temp_fr: float = 0.0
    brake_temp_rl: float = 0.0
    brake_temp_rr: float = 0.0
    
    # 悬挂行程
    suspension_fl: float = 0.0
    suspension_fr: float = 0.0
    suspension_rl: float = 0.0
    suspension_rr: float = 0.0
    
    # 车身高度
    ride_height_front: float = 0.0
    ride_height_rear: float = 0.0
    
    # 燃油/能量
    fuel: float = 0.0                # 剩余燃油（升）
    fuel_per_lap: float = 0.0        # 每圈油耗
    
    # 动力系统
    turbo_boost: float = 0.0
    ers_charge: float = 0.0
    ers_power_level: int = 0
    kers_charge: float = 0.0
    kers_input: float = 0.0
    
    # 辅助系统
    tc_level: int = 0                # 牵引力控制等级
    abs_level: int = 0               # ABS等级
    brake_bias: float = 0.0          # 刹车前后比
    engine_brake: int = 0            # 发动机制动
    
    # DRS
    drs_available: int = 0
    drs_enabled: int = 0
    
    # 损伤
    damage_front: float = 0.0
    damage_rear: float = 0.0
    damage_left: float = 0.0
    damage_right: float = 0.0
    damage_center: float = 0.0
    
    # 赛道/比赛状态
    is_in_pit: int = 0
    is_in_pit_lane: int = 0
    pit_limiter_on: int = 0
    sector_index: int = 0
    tyres_out: int = 0
    
    # 环境
    air_temp: float = 0.0
    road_temp: float = 0.0
    wind_speed: float = 0.0
    wind_direction: float = 0.0
    
    # 力反馈
    final_ff: float = 0.0
    
    # 比赛信息
    position: int = 0                # 排名
    flag: int = 0                    # 旗帜状态


@dataclass 
class SessionInfo:
    """会话信息"""
    car_model: str = ""
    track: str = ""
    track_config: str = ""
    player_name: str = ""
    max_rpm: int = 8000
    max_fuel: float = 0.0
    track_length: float = 0.0
    start_time: str = ""
    
    
class TelemetryLogger:
    """遥测数据日志记录器"""
    
    # 采样间隔（毫秒）- 用于控制日志大小
    # 25Hz (40ms) 提供更细致的数据，同时保持合理的文件大小
    SAMPLE_INTERVAL_MS = 40
    
    # RaceChrono 兼容的 CSV 表头映射
    RACECHRONO_HEADERS = [
        ("timestamp", "Time (s)"),
        ("lap_number", "Lap #"),
        ("lap_time_ms", "Lap Time (ms)"),
        ("speed_kmh", "Speed (km/h)"),
        ("speed_ms", "Speed (m/s)"),
        ("throttle", "Throttle (%)"),
        ("brake", "Brake (%)"),
        ("clutch", "Clutch (%)"),
        ("steering", "Steering Angle (deg)"),
        ("gear", "Gear"),
        ("rpm", "Engine RPM"),
        ("g_lateral", "Lateral Accel (G)"),
        ("g_longitudinal", "Longitudinal Accel (G)"),
        ("g_vertical", "Vertical Accel (G)"),
        ("heading", "Heading (deg)"),
        ("pitch", "Pitch (deg)"),
        ("roll", "Roll (deg)"),
        ("normalized_pos", "Track Position"),
        ("distance_traveled", "Distance (m)"),
        ("world_pos_x", "Position X (m)"),
        ("world_pos_y", "Position Y (m)"),
        ("world_pos_z", "Position Z (m)"),
        ("velocity_x", "Velocity X (m/s)"),
        ("velocity_y", "Velocity Y (m/s)"),
        ("velocity_z", "Velocity Z (m/s)"),
        ("angular_vel_x", "Angular Vel X (rad/s)"),
        ("angular_vel_y", "Angular Vel Y (rad/s)"),
        ("angular_vel_z", "Angular Vel Z (rad/s)"),
        ("tyre_slip_fl", "Tyre Slip FL"),
        ("tyre_slip_fr", "Tyre Slip FR"),
        ("tyre_slip_rl", "Tyre Slip RL"),
        ("tyre_slip_rr", "Tyre Slip RR"),
        ("tyre_load_fl", "Tyre Load FL (N)"),
        ("tyre_load_fr", "Tyre Load FR (N)"),
        ("tyre_load_rl", "Tyre Load RL (N)"),
        ("tyre_load_rr", "Tyre Load RR (N)"),
        ("tyre_pressure_fl", "Tyre Pressure FL (psi)"),
        ("tyre_pressure_fr", "Tyre Pressure FR (psi)"),
        ("tyre_pressure_rl", "Tyre Pressure RL (psi)"),
        ("tyre_pressure_rr", "Tyre Pressure RR (psi)"),
        ("tyre_temp_fl", "Tyre Temp FL (C)"),
        ("tyre_temp_fr", "Tyre Temp FR (C)"),
        ("tyre_temp_rl", "Tyre Temp RL (C)"),
        ("tyre_temp_rr", "Tyre Temp RR (C)"),
        ("tyre_wear_fl", "Tyre Wear FL (%)"),
        ("tyre_wear_fr", "Tyre Wear FR (%)"),
        ("tyre_wear_rl", "Tyre Wear RL (%)"),
        ("tyre_wear_rr", "Tyre Wear RR (%)"),
        ("brake_temp_fl", "Brake Temp FL (C)"),
        ("brake_temp_fr", "Brake Temp FR (C)"),
        ("brake_temp_rl", "Brake Temp RL (C)"),
        ("brake_temp_rr", "Brake Temp RR (C)"),
        ("suspension_fl", "Suspension FL (mm)"),
        ("suspension_fr", "Suspension FR (mm)"),
        ("suspension_rl", "Suspension RL (mm)"),
        ("suspension_rr", "Suspension RR (mm)"),
        ("ride_height_front", "Ride Height Front (mm)"),
        ("ride_height_rear", "Ride Height Rear (mm)"),
        ("fuel", "Fuel (L)"),
        ("fuel_per_lap", "Fuel Per Lap (L)"),
        ("turbo_boost", "Turbo Boost (bar)"),
        ("ers_charge", "ERS Charge (%)"),
        ("ers_power_level", "ERS Power Level"),
        ("kers_charge", "KERS Charge (kJ)"),
        ("tc_level", "TC Level"),
        ("abs_level", "ABS Level"),
        ("brake_bias", "Brake Bias (%)"),
        ("engine_brake", "Engine Brake"),
        ("drs_available", "DRS Available"),
        ("drs_enabled", "DRS Enabled"),
        ("damage_front", "Damage Front"),
        ("damage_rear", "Damage Rear"),
        ("damage_left", "Damage Left"),
        ("damage_right", "Damage Right"),
        ("damage_center", "Damage Center"),
        ("is_in_pit", "In Pit"),
        ("is_in_pit_lane", "In Pit Lane"),
        ("pit_limiter_on", "Pit Limiter"),
        ("sector_index", "Sector"),
        ("tyres_out", "Tyres Out"),
        ("air_temp", "Air Temp (C)"),
        ("road_temp", "Road Temp (C)"),
        ("wind_speed", "Wind Speed (km/h)"),
        ("wind_direction", "Wind Direction (deg)"),
        ("final_ff", "Force Feedback"),
        ("position", "Position"),
        ("flag", "Flag"),
    ]
    
    def __init__(self, output_dir: str = "logs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._is_recording = False
        self._csv_file = None
        self._csv_writer = None
        self._start_time: float = 0.0
        self._current_filename: str = ""
        self._session_info: Optional[SessionInfo] = None
        self._record_count: int = 0
        
    @property
    def is_recording(self) -> bool:
        return self._is_recording
        
    @property
    def current_filename(self) -> str:
        return self._current_filename
        
    @property
    def record_count(self) -> int:
        return self._record_count
        
    def start_recording(self, session_info: SessionInfo) -> str:
        """开始记录"""
        if self._is_recording:
            self.stop_recording()
            
        self._session_info = session_info
        self._start_time = time.perf_counter()
        self._record_count = 0
        
        # 生成文件名: 时间_赛道_车辆.csv
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        track_name = self._sanitize_filename(session_info.track or "unknown_track")
        car_name = self._sanitize_filename(session_info.car_model or "unknown_car")
        
        self._current_filename = f"{timestamp}_{track_name}_{car_name}.csv"
        filepath = self.output_dir / self._current_filename
        
        # 打开CSV文件
        self._csv_file = open(filepath, 'w', newline='', encoding='utf-8')
        
        # 写入元数据注释（RaceChrono 兼容）
        self._csv_file.write(f"# AC Overlay Telemetry Log\n")
        self._csv_file.write(f"# Session Start: {session_info.start_time}\n")
        self._csv_file.write(f"# Car: {session_info.car_model}\n")
        self._csv_file.write(f"# Track: {session_info.track}\n")
        if session_info.track_config:
            self._csv_file.write(f"# Track Config: {session_info.track_config}\n")
        self._csv_file.write(f"# Player: {session_info.player_name}\n")
        self._csv_file.write(f"# Track Length: {session_info.track_length:.2f} m\n")
        self._csv_file.write(f"# Max RPM: {session_info.max_rpm}\n")
        self._csv_file.write(f"#\n")
        
        # 写入CSV表头
        headers = [h[1] for h in self.RACECHRONO_HEADERS]
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow(headers)
        
        self._is_recording = True
        return str(filepath)
        
    def stop_recording(self) -> Optional[str]:
        """停止记录"""
        if not self._is_recording:
            return None
            
        filepath = self.output_dir / self._current_filename
        
        if self._csv_file:
            self._csv_file.close()
            self._csv_file = None
            
        self._csv_writer = None
        self._is_recording = False
        
        return str(filepath)
        
    # 字段精度配置（小数位数）- 平衡精度与文件大小
    FIELD_PRECISION = {
        'timestamp': 3,          # 时间精确到毫秒
        'speed_kmh': 2,          # 速度2位小数（更精确的速度比对）
        'speed_ms': 3,           # m/s 3位小数
        'throttle': 2,           # 踏板输入2位小数（更细腻的输入分析）
        'brake': 2,
        'clutch': 2,
        'steering': 2,           # 方向盘2位小数
        'g_lateral': 3,          # G力3位小数（更精确的G值分析）
        'g_longitudinal': 3,
        'g_vertical': 3,
        'heading': 2,            # 姿态2位小数
        'pitch': 2,
        'roll': 2,
        'normalized_pos': 4,     # 赛道位置4位小数
        'distance_traveled': 2,  # 距离2位小数
        'world_pos_x': 2,        # 世界坐标2位小数
        'world_pos_y': 2,
        'world_pos_z': 2,
        'velocity_x': 3,         # 速度分量3位小数
        'velocity_y': 3,
        'velocity_z': 3,
        'angular_vel_x': 3,
        'angular_vel_y': 3,
        'angular_vel_z': 3,
        'tyre_slip_fl': 3,       # 轮胎打滑3位（重要数据）
        'tyre_slip_fr': 3,
        'tyre_slip_rl': 3,
        'tyre_slip_rr': 3,
        'tyre_load_fl': 0,       # 轮胎负载整数
        'tyre_load_fr': 0,
        'tyre_load_rl': 0,
        'tyre_load_rr': 0,
        'tyre_pressure_fl': 1,   # 胎压1位
        'tyre_pressure_fr': 1,
        'tyre_pressure_rl': 1,
        'tyre_pressure_rr': 1,
        'tyre_temp_fl': 1,       # 温度1位
        'tyre_temp_fr': 1,
        'tyre_temp_rl': 1,
        'tyre_temp_rr': 1,
        'brake_temp_fl': 0,      # 刹车温度整数
        'brake_temp_fr': 0,
        'brake_temp_rl': 0,
        'brake_temp_rr': 0,
        'suspension_fl': 2,      # 悬挂2位小数
        'suspension_fr': 2,
        'suspension_rl': 2,
        'suspension_rr': 2,
        'ride_height_front': 2,
        'ride_height_rear': 2,
        'fuel': 2,
        'fuel_per_lap': 3,       # 油耗3位小数
        'turbo_boost': 2,
        'ers_charge': 1,
        'brake_bias': 1,
        'air_temp': 1,
        'road_temp': 1,
        'wind_speed': 1,
        'wind_direction': 0,
        'final_ff': 2,
    }
    
    def record(self, data: FullTelemetryData):
        """记录一条数据"""
        if not self._is_recording or not self._csv_writer:
            return
            
        # 更新相对时间
        data.timestamp = time.perf_counter() - self._start_time
        
        # 获取数据字典
        data_dict = asdict(data)
        
        # 按表头顺序提取值
        row = []
        for field_name, _ in self.RACECHRONO_HEADERS:
            value = data_dict.get(field_name, 0)
            # 格式化数值 - 使用配置的精度
            if isinstance(value, float):
                precision = self.FIELD_PRECISION.get(field_name, 3)  # 默认3位
                if precision == 0:
                    row.append(str(int(round(value))))
                else:
                    row.append(f"{value:.{precision}f}")
            else:
                row.append(str(value))
                
        self._csv_writer.writerow(row)
        self._record_count += 1
        
        # 每100条刷新一次，防止数据丢失
        if self._record_count % 100 == 0:
            self._csv_file.flush()
            
    def _sanitize_filename(self, name: str) -> str:
        """清理文件名中的非法字符"""
        # 替换常见非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        # 去除前后空格，限制长度
        return name.strip()[:50]
        
    def __del__(self):
        """析构时确保文件关闭"""
        if self._is_recording:
            self.stop_recording()
