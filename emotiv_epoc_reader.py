import hid
import time
from Crypto.Cipher import AES

# Function to generate AES key based on device serial number
def generate_aes_key(serial_number):
    """
    Emotiv AES key format: 16-byte key
    For Epoc+ Premium: full serial (ASCII), padded with 0x00 if needed
    """
    serial_bytes = serial_number.encode('ascii')
    key = serial_bytes + b'\x00' * (16 - len(serial_bytes))
    return key

def run():
    for device in hid.enumerate():
        if (
            device['manufacturer_string'] and 'Emotiv' in device['manufacturer_string'] and
            device.get('interface_number', -1) == 1  # Use interface 1 for EEG data
        ):
            print(f"Product found: {device['product_string']}")
            print(f"Serial: {device['serial_number']}")
            print(f"Path: {device['path']}")
            
            serial = device['serial_number']
            key = generate_aes_key(serial)
            connect_device(device['path'], key)

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
            decrypted = cipher.decrypt(bytes(data[:16]))  # Only decrypt the first 16 bytes
            print(f"Raw: {data}")
            print(f"Decrypted: {list(decrypted)}")
        else:
            print(".", end="", flush=True)
            time.sleep(0.2)

if __name__ == "__main__":
    run()
