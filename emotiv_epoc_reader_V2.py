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

# Bit masks for EPOC+ EEG channels (14 bits per channel)
EEG_BIT_MASKS = {
    "AF3": [10,11,12,13,14,15,0,1,2,3,4,5,6,7],
    "F7":  [28,29,30,31,16,17,18,19,20,21,22,23,8,9],
    "F3":  [46,47,32,33,34,35,36,37,38,39,24,25,26,27],
    "FC5": [48,49,50,51,52,53,54,55,40,41,42,43,44,45],
    "T7":  [66,67,68,69,70,71,56,57,58,59,60,61,62,63],
    "P7":  [84,85,86,87,72,73,74,75,76,77,78,79,64,65],
    "O1":  [102,103,88,89,90,91,92,93,94,95,80,81,82,83],
    "O2":  [120,121,122,123,108,109,110,111,96,97,98,99,100,101],
    "P8":  [138,139,124,125,126,127,128,129,130,131,116,117,118,119],
    "T8":  [156,157,158,159,144,145,146,147,132,133,134,135,136,137],
    "FC6": [160,161,162,163,164,165,166,167,148,149,150,151,152,153],
    "F4":  [178,179,180,181,182,183,168,169,170,171,172,173,174,175],
    "F8":  [196,197,198,199,184,185,186,187,188,189,190,191,176,177],
    "AF4": [214,215,200,201,202,203,204,205,206,207,192,193,194,195],
}

# AES key based on device serial number
def generate_aes_key(serial_number: str) -> bytes:
    serial_bytes = serial_number.encode("ascii")
    return serial_bytes + b"\x00" * (16 - len(serial_bytes))

def get_channel_value(packet: list[int], channel: str) -> int:
    """
    Correctly reconstruct 14-bit EEG value for EPOC+ using bit masks.
    """
    bits = EEG_BIT_MASKS[channel]
    value = 0

    for i, bit_index in enumerate(bits):
        byte_index = bit_index // 8
        bit_offset = bit_index % 8

        if packet[byte_index] & (1 << bit_offset):
            value |= (1 << i)

    return value  # 0–16383


def extract_all_channels(packet: list[int]) -> dict[str, int]:
    return {ch: get_channel_value(packet, ch) for ch in CHANNELS}

def extract_gyro(packet: list[int]) -> dict[str, int]:
    """Extracts gyroX, gyroY (signed values)."""
    gx = packet[29] - 128
    gy = packet[30] - 128
    return {"gyroX": gx, "gyroY": gy}

def to_microvolts(raw):
    return (raw - 8192) * 0.51

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
            gyro = extract_gyro(packet)

            # Print numeric values
            print(f"EEG: {to_microvolts(eeg)}")
            print(f"Gyro: {gyro}")
            print("-" * 40)
        else:
            print(".", end="", flush=True)
            time.sleep(0.2)

if __name__ == "__main__":
    run()