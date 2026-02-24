"""
Assetto Corsa 共享内存读取器
"""

import math
import mmap
import ctypes
from typing import Optional
from dataclasses import dataclass

from ac_structs import SPageFilePhysics, SPageFileGraphic, SPageFileStatic
from telemetry_logger import FullTelemetryData, SessionInfo


@dataclass
class TelemetryData:
    """遥测数据（简化版，用于UI显示）"""
    # 输入
    throttle: float = 0.0      # 油门 0-1
    brake: float = 0.0         # 刹车 0-1
    clutch: float = 0.0        # 离合 0-1
    steer_angle: float = 0.0   # 方向盘角度 (弧度)
    
    # 运动状态
    speed_kmh: float = 0.0     # 速度 km/h
    gear: int = 0              # 挡位
    rpm: int = 0               # 转速
    
    # G力
    g_lateral: float = 0.0     # 横向G
    g_longitudinal: float = 0.0 # 纵向G
    
    # 状态
    is_connected: bool = False
    is_driving: bool = False    # 是否在驾驶（速度>0或有输入）


class ACSharedMemory:
    """AC共享内存读取器"""
    
    PHYSICS_MAP_NAME = "Local\\acpmf_physics"
    GRAPHICS_MAP_NAME = "Local\\acpmf_graphics"
    STATIC_MAP_NAME = "Local\\acpmf_static"
    
    def __init__(self):
        self._physics_mmap: Optional[mmap.mmap] = None
        self._graphics_mmap: Optional[mmap.mmap] = None
        self._static_mmap: Optional[mmap.mmap] = None
        self._connected = False
        self._cached_static: Optional[SPageFileStatic] = None
        
    def connect(self) -> bool:
        """连接到AC共享内存"""
        try:
            self._physics_mmap = mmap.mmap(-1, ctypes.sizeof(SPageFilePhysics), 
                                           self.PHYSICS_MAP_NAME, access=mmap.ACCESS_READ)
            self._graphics_mmap = mmap.mmap(-1, ctypes.sizeof(SPageFileGraphic), 
                                            self.GRAPHICS_MAP_NAME, access=mmap.ACCESS_READ)
            self._static_mmap = mmap.mmap(-1, ctypes.sizeof(SPageFileStatic), 
                                          self.STATIC_MAP_NAME, access=mmap.ACCESS_READ)
            self._connected = True
            self._cached_static = None  # 清除缓存
            return True
        except Exception as e:
            print(f"无法连接到AC共享内存: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        for mm in [self._physics_mmap, self._graphics_mmap, self._static_mmap]:
            if mm:
                try:
                    mm.close()
                except:
                    pass
        self._physics_mmap = None
        self._graphics_mmap = None
        self._static_mmap = None
        self._connected = False
        self._cached_static = None
    
    def read_physics(self) -> Optional[SPageFilePhysics]:
        """读取物理数据"""
        if not self._physics_mmap:
            return None
        try:
            self._physics_mmap.seek(0)
            data = self._physics_mmap.read(ctypes.sizeof(SPageFilePhysics))
            return SPageFilePhysics.from_buffer_copy(data)
        except:
            return None
    
    def read_graphics(self) -> Optional[SPageFileGraphic]:
        """读取图形数据"""
        if not self._graphics_mmap:
            return None
        try:
            self._graphics_mmap.seek(0)
            data = self._graphics_mmap.read(ctypes.sizeof(SPageFileGraphic))
            return SPageFileGraphic.from_buffer_copy(data)
        except:
            return None
            
    def read_static(self) -> Optional[SPageFileStatic]:
        """读取静态数据"""
        if not self._static_mmap:
            return None
        try:
            self._static_mmap.seek(0)
            data = self._static_mmap.read(ctypes.sizeof(SPageFileStatic))
            return SPageFileStatic.from_buffer_copy(data)
        except:
            return None
    
    def get_session_info(self) -> Optional[SessionInfo]:
        """获取会话信息（用于日志文件名等）"""
        if not self._connected:
            if not self.connect():
                return None
                
        static = self.read_static()
        if not static:
            return None
            
        # 缓存静态数据
        self._cached_static = static
        
        return SessionInfo(
            car_model=static.carModel.rstrip('\x00'),
            track=static.track.rstrip('\x00'),
            track_config=static.trackConfiguration.rstrip('\x00'),
            player_name=f"{static.playerName.rstrip(chr(0))} {static.playerSurname.rstrip(chr(0))}".strip(),
            max_rpm=static.maxRpm,
            max_fuel=static.maxFuel,
            track_length=static.trackSPlineLength,
            start_time=""  # 由调用者设置
        )
    
    def get_telemetry(self) -> TelemetryData:
        """获取遥测数据（简化版，用于UI）"""
        result = TelemetryData()
        
        if not self._connected:
            if not self.connect():
                return result
        
        physics = self.read_physics()
        graphics = self.read_graphics()
        
        if physics and graphics:
            result.is_connected = True
            result.throttle = physics.gas
            result.brake = physics.brake
            result.clutch = physics.clutch
            result.steer_angle = physics.steerAngle
            result.speed_kmh = physics.speedKmh
            result.gear = physics.gear
            result.rpm = physics.rpms
            result.g_lateral = physics.accG[0]
            result.g_longitudinal = physics.accG[2]
            
            # 判断是否在驾驶
            result.is_driving = (
                physics.speedKmh > 1.0 or 
                physics.gas > 0.01 or 
                physics.brake > 0.01 or
                graphics.status == 2  # LIVE状态
            )
        else:
            result.is_connected = False
            # 尝试重新连接
            self.disconnect()
            
        return result
        
    def get_full_telemetry(self) -> Optional[FullTelemetryData]:
        """获取完整遥测数据（用于日志记录）"""
        if not self._connected:
            if not self.connect():
                return None
                
        physics = self.read_physics()
        graphics = self.read_graphics()
        
        if not physics or not graphics:
            return None
            
        data = FullTelemetryData()
        
        # 时间信息
        data.lap_number = graphics.completedLaps
        data.lap_time_ms = graphics.iCurrentTime
        
        # 车辆输入
        data.throttle = physics.gas * 100  # 转为百分比
        data.brake = physics.brake * 100
        data.clutch = physics.clutch * 100
        data.steering = math.degrees(physics.steerAngle)  # 转为度
        
        # 运动状态
        data.speed_kmh = physics.speedKmh
        data.speed_ms = physics.speedKmh / 3.6
        data.gear = physics.gear
        data.rpm = physics.rpms
        
        # 速度向量
        data.velocity_x = physics.velocity[0]
        data.velocity_y = physics.velocity[1]
        data.velocity_z = physics.velocity[2]
        
        # G力
        data.g_lateral = physics.accG[0]
        data.g_longitudinal = physics.accG[2]
        data.g_vertical = physics.accG[1]
        
        # 车辆姿态
        data.heading = math.degrees(physics.heading)
        data.pitch = math.degrees(physics.pitch)
        data.roll = math.degrees(physics.roll)
        
        # 角速度
        data.angular_vel_x = physics.localAngularVel[0]
        data.angular_vel_y = physics.localAngularVel[1]
        data.angular_vel_z = physics.localAngularVel[2]
        
        # 位置
        data.normalized_pos = graphics.normalizedCarPosition
        data.distance_traveled = graphics.distanceTraveled
        
        # 世界坐标 - 从 carCoordinates 获取玩家车辆位置
        player_id = graphics.playerCarID
        if 0 <= player_id < 60:
            # carCoordinates 是 [60][3] 数组，需要使用二维索引
            data.world_pos_x = float(graphics.carCoordinates[player_id][0])
            data.world_pos_y = float(graphics.carCoordinates[player_id][1])
            data.world_pos_z = float(graphics.carCoordinates[player_id][2])
        
        # 轮胎数据 [FL, FR, RL, RR]
        data.tyre_slip_fl = physics.wheelSlip[0]
        data.tyre_slip_fr = physics.wheelSlip[1]
        data.tyre_slip_rl = physics.wheelSlip[2]
        data.tyre_slip_rr = physics.wheelSlip[3]
        
        data.tyre_load_fl = physics.wheelLoad[0]
        data.tyre_load_fr = physics.wheelLoad[1]
        data.tyre_load_rl = physics.wheelLoad[2]
        data.tyre_load_rr = physics.wheelLoad[3]
        
        data.tyre_pressure_fl = physics.wheelsPressure[0]
        data.tyre_pressure_fr = physics.wheelsPressure[1]
        data.tyre_pressure_rl = physics.wheelsPressure[2]
        data.tyre_pressure_rr = physics.wheelsPressure[3]
        
        data.tyre_temp_fl = physics.tyreCoreTemperature[0]
        data.tyre_temp_fr = physics.tyreCoreTemperature[1]
        data.tyre_temp_rl = physics.tyreCoreTemperature[2]
        data.tyre_temp_rr = physics.tyreCoreTemperature[3]
        
        data.tyre_wear_fl = physics.tyreWear[0]
        data.tyre_wear_fr = physics.tyreWear[1]
        data.tyre_wear_rl = physics.tyreWear[2]
        data.tyre_wear_rr = physics.tyreWear[3]
        
        # 刹车温度
        data.brake_temp_fl = physics.brakeTemp[0]
        data.brake_temp_fr = physics.brakeTemp[1]
        data.brake_temp_rl = physics.brakeTemp[2]
        data.brake_temp_rr = physics.brakeTemp[3]
        
        # 悬挂行程 (转换为mm)
        data.suspension_fl = physics.suspensionTravel[0] * 1000
        data.suspension_fr = physics.suspensionTravel[1] * 1000
        data.suspension_rl = physics.suspensionTravel[2] * 1000
        data.suspension_rr = physics.suspensionTravel[3] * 1000
        
        # 车身高度 (转换为mm)
        data.ride_height_front = physics.rideHeight[0] * 1000
        data.ride_height_rear = physics.rideHeight[1] * 1000
        
        # 燃油
        data.fuel = physics.fuel
        data.fuel_per_lap = graphics.fuelXLap
        
        # 动力系统
        data.turbo_boost = physics.turboBoost
        data.ers_charge = physics.kersCharge * 100  # 转为百分比
        data.ers_power_level = physics.ersPowerLevel
        data.kers_charge = physics.kersCurrentKJ
        data.kers_input = physics.kersInput
        
        # 辅助系统
        data.tc_level = graphics.TC
        data.abs_level = graphics.ABS
        data.brake_bias = physics.brakeBias * 100
        data.engine_brake = physics.engineBrake
        
        # DRS
        data.drs_available = physics.drsAvailable
        data.drs_enabled = physics.drsEnabled
        
        # 损伤
        data.damage_front = physics.carDamage[0]
        data.damage_rear = physics.carDamage[1]
        data.damage_left = physics.carDamage[2]
        data.damage_right = physics.carDamage[3]
        data.damage_center = physics.carDamage[4]
        
        # 赛道/比赛状态
        data.is_in_pit = graphics.isInPit
        data.is_in_pit_lane = graphics.isInPitLane
        data.pit_limiter_on = physics.pitLimiterOn
        data.sector_index = graphics.currentSectorIndex
        data.tyres_out = physics.numberOfTyresOut
        
        # 环境
        data.air_temp = physics.airTemp
        data.road_temp = physics.roadTemp
        data.wind_speed = graphics.windSpeed
        data.wind_direction = graphics.windDirection
        
        # 力反馈
        data.final_ff = physics.finalFF
        
        # 比赛信息
        data.position = graphics.position
        data.flag = graphics.flag
        
        return data
    
    @property
    def is_connected(self) -> bool:
        return self._connected