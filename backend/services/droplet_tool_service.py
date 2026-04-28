"""液滴分配工具服务"""

import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ——— 通信协议常量 ———
OUTPUT_TYPE_MAP = {
    'ElectrodeOnly'     : 0x01,
    'PowerOnly'         : 0x02,
    'ElectrodeAndPower' : 0x08,
}


def build_frame(nodes: list,
                voltage: int = 80,
                ac_on: bool = True,
                freq: int = 100,
                output_type: str = 'ElectrodeOnly') -> bytes:
    """
    构造一整帧（29 字节：帧头+长度+24 字节 Data+CRC+帧尾）：
      [0–1]  DD D1
      [2]    长度 = 0x18
      [3]   Data[0] = OutputType
      [4–19] Data[1–16] = 电极位图
      [20]   Data[17] = 电压码（ElectrodeOnly 下填 0）
      [21]   Data[18] = AC 开关（ElectrodeOnly 下填 0）
      [22–23] Data[19–20] = 频率（ElectrodeOnly 下填 0）
      [24–26] Data[21–23] = 保留 0
      [27]   CRC = (长度 + sum(Data)) & 0xFF
      [28]   帧尾 = 0x0A
    """
    if output_type not in OUTPUT_TYPE_MAP:
        raise ValueError(f"Unknown output_type: {output_type}")

    # 24 字节 Data 区
    data = bytearray(24)
    data[0] = OUTPUT_TYPE_MAP[output_type]

    # 电极位图
    for n in nodes:
        if not 1 <= n <= 128:
            raise ValueError(f"Electrode index out of range: {n}")
        grp = (n - 1) // 8       # 0–15
        bit = 7 - ((n - 1) % 8)  # 7–0
        data[1 + grp] |= (1 << bit)

    if output_type != 'ElectrodeOnly':
        # 电压反向线性映射（103→0, 46→255）
        Vmin, Vmax = 46.0, 103.0
        code = round((Vmax - voltage) / (Vmax - Vmin) * 255)
        data[17] = max(0, min(255, code))
        # AC 开关
        data[18] = 0x01 if ac_on else 0x00
        # 频率（大端）
        f = max(0, min(0xFFFF, int(freq)))
        data[19] = (f >> 8) & 0xFF
        data[20] = f & 0xFF

    # 构造完整帧
    frame = bytearray()
    frame += b'\xDD\xD1'         # 帧头
    frame.append(0x18)           # 长度
    frame += data                # Data
    crc = (0x18 + sum(data)) & 0xFF
    frame.append(crc)            # CRC
    frame.append(0x0A)           # 帧尾

    return bytes(frame)


class DropletToolService:
    """液滴分配工具服务，封装串口通信与帧发送逻辑。"""

    def __init__(self, serial_config: dict):
        """
        Args:
            serial_config: 串口配置字典，支持以下键：
                - port: 串口号，默认 'COM6'
                - baud_rate: 波特率，默认 115200
                - mock_mode: 是否模拟模式（不打开真实串口），默认 False
        """
        self.port: str = serial_config.get('port', 'COM6')
        self.baud_rate: int = serial_config.get('baud_rate', 115200)
        self.mock_mode: bool = serial_config.get('mock_mode', False)
        logger.info(
            "DropletToolService 初始化: port=%s, baud_rate=%d, mock_mode=%s",
            self.port, self.baud_rate, self.mock_mode,
        )

    def execute_dispense(
        self,
        electrode_sequences: list,
        interval: float = 1.0,
        voltage: int = 80,
        output_type: str = 'ElectrodeOnly',
    ) -> dict:
        """执行液滴分配操作。

        Args:
            electrode_sequences: 多个液滴的时间步序列。
                格式: [[[58,5,6],[5,6,22],...], [[58,5,6],[5,6,50],...]]
                每个元素代表一个液滴的完整路径，内部每个子列表是该时间步同时激活的电极编号。
            interval: 每个时间步之间的间隔秒数，默认 1.0
            voltage: 电压值，默认 80
            output_type: 输出类型，默认 'ElectrodeOnly'

        Returns:
            dict: {"success": bool, "total_steps": int, "executed_steps": int, "log_messages": list[str]}
        """
        log_messages: List[str] = []
        executed_steps = 0

        if not electrode_sequences:
            return {
                "success": False,
                "total_steps": 0,
                "executed_steps": 0,
                "log_messages": ["electrode_sequences 为空，无操作"],
            }

        # 总时间步数取所有液滴路径中最长的
        total_steps = max(len(seq) for seq in electrode_sequences)

        try:
            if self.mock_mode:
                # ——— Mock 模式：仅生成帧数据和日志，不打开串口 ———
                for t in range(total_steps):
                    nodes: List[int] = []
                    for seq in electrode_sequences:
                        if t < len(seq):
                            nodes += seq[t]

                    frame = build_frame(nodes, voltage=voltage, output_type=output_type)
                    msg = f"t={t:02d} Sent: {frame.hex(' ').upper()}"
                    logger.info(msg)
                    log_messages.append(msg)
                    executed_steps += 1

                    if t < total_steps - 1:
                        time.sleep(interval)
            else:
                # ——— 真实模式：通过串口发送帧 ———
                import serial as _serial

                with _serial.Serial(
                    self.port,
                    baudrate=self.baud_rate,
                    bytesize=_serial.EIGHTBITS,
                    parity=_serial.PARITY_NONE,
                    stopbits=_serial.STOPBITS_ONE,
                    timeout=0.1,
                ) as ser:
                    for t in range(total_steps):
                        nodes = []
                        for seq in electrode_sequences:
                            if t < len(seq):
                                nodes += seq[t]

                        frame = build_frame(nodes, voltage=voltage, output_type=output_type)
                        ser.write(frame)
                        ser.flush()

                        msg = f"t={t:02d} Sent: {frame.hex(' ').upper()}"
                        logger.info(msg)
                        log_messages.append(msg)
                        executed_steps += 1

                        if t < total_steps - 1:
                            time.sleep(interval)

            return {
                "success": True,
                "total_steps": total_steps,
                "executed_steps": executed_steps,
                "log_messages": log_messages,
            }

        except Exception as e:
            error_msg = f"液滴分配执行异常: {e}"
            logger.error(error_msg, exc_info=True)
            log_messages.append(error_msg)
            return {
                "success": False,
                "total_steps": total_steps,
                "executed_steps": executed_steps,
                "log_messages": log_messages,
            }
