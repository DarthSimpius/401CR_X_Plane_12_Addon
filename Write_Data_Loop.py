import ctypes
import mmap
import socket
import struct
import time

class TelemetryCompat(ctypes.Structure):
    _fields_ = [
        ("IsOnTrack", ctypes.c_ubyte),
        ("Lateral", ctypes.c_double),
        ("Longitudinal", ctypes.c_double),
        ("Vertical", ctypes.c_double),
        ("Pitch", ctypes.c_double),
        ("Roll", ctypes.c_double),
        ("Yaw", ctypes.c_double),
        ("PositionX", ctypes.c_double),
        ("PositionY", ctypes.c_double),
        ("PositionZ", ctypes.c_double),
        ("VelocityX", ctypes.c_double),
        ("VelocityY", ctypes.c_double),
        ("VelocityZ", ctypes.c_double),
        ("SpinX", ctypes.c_double),
        ("SpinY", ctypes.c_double),
        ("SpinZ", ctypes.c_double),
        ("WheelSpeedFL", ctypes.c_double),
        ("WheelSpeedFR", ctypes.c_double),
        ("WheelSpeedRL", ctypes.c_double),
        ("WheelSpeedRR", ctypes.c_double),
        ("RPM", ctypes.c_double),
        ("Speed", ctypes.c_double),
        ("Gear", ctypes.c_double),
        ("Throttle", ctypes.c_double),
        ("Brake", ctypes.c_double),
        ("Clutch", ctypes.c_double),
        ("Steering", ctypes.c_double),
        ("ABS", ctypes.c_double),
        ("SlipAngle", ctypes.c_double),
        ("PacketTime", ctypes.c_longlong),
    ]

#SHARED MEMORY SECTION
#---------------------
SHM_Name = "TelemetryData"
SHM_Size = ctypes.sizeof(TelemetryCompat)

def open_shared_memory():

    return mmap.mmap(-1,
        SHM_Size,
        tagname=SHM_Name,
        access=mmap.ACCESS_WRITE
    )

def write_telemetry(shm, data: TelemetryCompat):
    raw = bytes(data)
    shm.seek(0)
    shm.write(raw)
#--------------------

#XPLANE UDP LISTENER
#-------------------
UDP_Port = 49001
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind("127.0.0.1", UDP_Port)
#-------------------

def main():
    shm = open_shared_memory()
    
    telemetry = TelemetryCompat()

    while True:
        packet, addr = sock.recvfrom(2048)

        if packet[0:5] != b"DATA\0":
            continue
        for offset in range(5, len(packet), 36):
            row = packet[offset:offset+36]
            if len(row) < 36:
                continue
            idx, *values = struct.unpack("<i8f", row)

            if idx == 3:    # Pitch, Roll, Heading (degrees)
                # Multiply by 0.0174533 to convert degrees to radians
                telemetry.Pitch = values[0] * 0.0174533
                telemetry.Roll = values[1] * 0.0174533
                telemetry.Yaw = values[2] * 0.0174533
            elif idx == 16:  # Local velocities (m/s)
                telemetry.VelocityX = values[0]
                telemetry.VelocityY = values[1]
                telemetry.VelocityZ = values[2]

            elif idx == 17:  # Local accelerations (g)
                telemetry.Lateral      = values[0]
                telemetry.Longitudinal = values[1]
                telemetry.Vertical     = values[2]

            elif idx == 20:  # Angular rates (deg/s)
                # Multiply by 0.0174533 to convert degrees to radians
                telemetry.SpinX = values[0] * 0.0174533
                telemetry.SpinY = values[1] * 0.0174533
                telemetry.SpinZ = values[2] * 0.0174533

            elif idx == 21:  # Engine RPM
                telemetry.RPM = values[0]

            elif idx == 37:  # Throttle, brake, gear
                telemetry.Throttle = values[0]
                telemetry.Brake    = values[2]
                telemetry.Gear     = values[5]
        telemetry.PacketTime = int(time.time() * 1000)
        telemetry.IsOnTrack = 1

        write_telemetry(shm, telemetry)

if __name__ == "__main__":
    main()