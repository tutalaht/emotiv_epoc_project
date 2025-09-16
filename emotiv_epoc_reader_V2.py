import hid
import time
from Crypto.Cipher import AES

# Channel mapping for Epoc+ (14-bit values)
CHANNELS = {
    "AF3": 0,
    "F7": 1,
    "F3": 2,
    "FC5": 3,
    "T7": 4,
    "P7": 5,
    "O1": 6,
    "O2": 7,
    "P8": 8,
    "T8": 9,
    "FC6": 10,
    "F4": 11,
    "F8": 12,
    "AF4": 13,
}

# AES key based on device serial number
def generate_aes_key(serial_number: str) -> bytes:
    serial_bytes = serial_number.encode("ascii")
    return serial_bytes + b"\x00" * (16 - len(serial_bytes))

def get_channel_value(packet: list[int], channel: str) -> int:
    """Extract 14-bit EEG channel value from decrypted packet."""
    index = CHANNELS[channel]
    lo = packet[2 * index + 1]
    hi = packet[2 * index + 2]
    val = ((hi & 0xFF) << 8) | lo
    return val & 0x3FFF  # 14-bit mask

def extract_all_channels(packet: list[int]) -> dict[str, int]:
    return {ch: get_channel_value(packet, ch) for ch in CHANNELS}

def extract_quality(packet: list[int]) -> dict[str, int]:
    """
    Extract contact quality for each channel.
    Returns 0-15 scale (0=bad, 15=perfect).
    """
    quality = {}
    for ch, idx in CHANNELS.items():
        hi = packet[2 * idx + 2]
        q = (hi >> 4) & 0x0F  # 4-bit quality (0-15)
        quality[ch] = q
    return quality

def extract_gyro(packet: list[int]) -> dict[str, int]:
    """Extracts gyroX, gyroY (signed values)."""
    gx = packet[29] - 128
    gy = packet[30] - 128
    return {"gyroX": gx, "gyroY": gy}

def run():
    for device in hid.enumerate():
        if (
            device["manufacturer_string"]
            and "Emotiv" in device["manufacturer_string"]
            and device.get("interface_number", -1) == 1
        ):
            print(f"Product found: {device['product_string']}")
            print(f"Serial: {device['serial_number']}")
            print(f"Path: {device['path']}")

            serial = device["serial_number"]
            key = generate_aes_key(serial)
            connect_device(device["path"], key)

def connect_device(path, key):
    device = hid.device()
    device.open_path(path)
    device.set_nonblocking(True)

    cipher = AES.new(key, AES.MODE_ECB)

    print("Waiting for data...")

    timeout = time.time() + 10  # Try for 10 seconds

    while time.time() < timeout:
        data = device.read(32)
        
        if data:
            # Decrypt both 16-byte blocks
            block1 = cipher.decrypt(bytes(data[0:16]))
            block2 = cipher.decrypt(bytes(data[16:32]))
            packet = list(block1 + block2)  # full 32-byte decrypted frame

            eeg = extract_all_channels(packet)
            quality = extract_quality(packet)
            gyro = extract_gyro(packet)

            # Print numeric values
            print(f"EEG: {eeg}")
            print(f"Quality: {quality}")
            print(f"Gyro: {gyro}")
            print("-" * 40)
        else:
            print(".", end="", flush=True)
            time.sleep(0.2)

if __name__ == "__main__":
    run()