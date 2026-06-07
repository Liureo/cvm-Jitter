import threading
import serial
from serial.tools import list_ports
import time

makcu = None
makcu_lock = threading.Lock()
button_states = {i: False for i in range(5)}
button_states_lock = threading.Lock()
is_connected = False
connected_port = None
connected_baud = None
last_value = 0

SUPPORTED_DEVICES = [
    ("1A86:55D3", "MAKCU"),
    ("1A86:5523", "CH343"),
    ("1A86:7523", "CH340"),
    ("1A86:5740", "CH347"),
    ("10C4:EA60", "CP2102"),
]
SUPPORTED_BAUD_RATES = (115_200, 4_000_000)

def find_com_ports():
    found = []
    for port in list_ports.comports():
        hwid = port.hwid.upper()
        desc = port.description.upper()
        for vidpid, name in SUPPORTED_DEVICES:
            if vidpid in hwid or name.upper() in desc:
                found.append((port.device, name))
                break
    return found

def list_com_ports():
    """Return all serial ports so the UI can also select devices manually."""
    return [(port.device, port.description) for port in list_ports.comports()]

def km_version_ok(ser):
    try:
        ser.reset_input_buffer()
        ser.write(b"km.version()\r")
        ser.flush()
        time.sleep(0.1)
        resp = b""
        start = time.time()
        while time.time() - start < 0.3:
            if ser.in_waiting:
                resp += ser.read(ser.in_waiting)
                if b"km.MAKCU" in resp or b"MAKCU" in resp:
                    return True
            time.sleep(0.01)
        return False
    except Exception as e:
        print(f"[WARN] km_version_ok: {e}")
        return False

def connect_to_makcu(preferred_port=None, baud_rate=115_200):
    global makcu, is_connected, connected_port, connected_baud
    if baud_rate not in SUPPORTED_BAUD_RATES:
        print(f"[ERROR] Unsupported baud rate: {baud_rate}")
        return False

    detected_ports = find_com_ports()
    if preferred_port:
        matched = next(
            ((port, name) for port, name in detected_ports if port == preferred_port),
            None,
        )
        ports = [matched or (preferred_port, "SERIAL")]
    else:
        ports = detected_ports

    if not ports:
        print("[ERROR] No supported serial devices found.")
        return False

    for port_name, dev_name in ports:
        print(f"[INFO] Connecting to {dev_name} {port_name} @ {baud_rate}...")
        try:
            makcu = serial.Serial(port_name, baud_rate, timeout=0.1)
            time.sleep(0.1)
            if dev_name == "MAKCU" and not km_version_ok(makcu):
                raise RuntimeError(
                    f"MAKCU did not respond on {port_name} at {baud_rate} baud"
                )
            with makcu_lock:
                makcu.reset_input_buffer()
                makcu.write(b"km.buttons(1)\r")
                makcu.flush()
            is_connected = True
            connected_port = port_name
            connected_baud = baud_rate
            print(f"[INFO] Connected to {port_name} at {baud_rate} baud.")
            return True
        except Exception as e:
            print(f"[WARN] Failed {port_name}@{baud_rate}: {e}")
            if makcu and makcu.is_open:
                makcu.close()
            makcu = None
            is_connected = False
            connected_port = None
            connected_baud = None

    print("[ERROR] Could not connect to any supported device.")
    connected_port = None
    return False


def count_bits(n: int) -> int:
    return bin(n).count("1")

def listen_makcu():
    global last_value, is_connected
    # start from a clean state
    last_value = 0
    with button_states_lock:
        for i in range(5):
            button_states[i] = False

    while is_connected:
        try:
            b = makcu.read(1)  # blocking read (uses port timeout)
            if not b:
                continue

            v = b[0]

            # Ignore echoed ASCII (including CR/LF). Only 0..31 are valid masks.
            if v in (0x0A, 0x0D) or v > 31:
                continue

            # v is a 5-bit mask (bit0..bit4). Update only changed bits.
            changed = last_value ^ v
            if changed:
                with button_states_lock:
                    for i in range(5):
                        m = 1 << i
                        if changed & m:
                            button_states[i] = bool(v & m)
                last_value = v

        except serial.SerialException as e:
            print(f"[ERROR] Listener serial exception: {e}")
            is_connected = False
            break
        except Exception as e:
            # swallow transient errors but keep running
            print(f"[WARN] Listener error: {e}")
            time.sleep(0.001)

    # ensure clean state on exit
    with button_states_lock:
        for i in range(5):
            button_states[i] = False
    last_value = 0

def is_button_pressed(idx: int) -> bool:
    with button_states_lock:
        return button_states.get(idx, False)

def test_move():
    if is_connected:
        with makcu_lock:
            makcu.write(b"km.move(100,100)\r")
            makcu.flush()

# --------------------------------------------------------------------
# Button Lock / Masking helpers
# --------------------------------------------------------------------

# Index mapping: 0=L, 1=R, 2=M, 3=S4, 4=S5
_LOCK_CMD_BY_IDX = {
    0: "lock_ml",
    1: "lock_mr",
    2: "lock_mm",
    3: "lock_ms1",
    4: "lock_ms2",
}

# State tracked by mask manager (so we only send lock/unlock when needed)
_mask_applied_idx = None

def _send_cmd_no_wait(cmd: str):
    """Send 'km.<cmd>\\r' without waiting for response (listener ignores ASCII)."""
    if not is_connected:
        return
    with makcu_lock:
        makcu.write(f"km.{cmd}\r".encode("ascii", "ignore"))
        makcu.flush()

def lock_button_idx(idx: int):
    """Lock a single button by index (0..4)."""
    cmd = _LOCK_CMD_BY_IDX.get(idx)
    if cmd is None:
        return
    _send_cmd_no_wait(f"{cmd}(1)")

def unlock_button_idx(idx: int):
    """Unlock a single button by index (0..4)."""
    cmd = _LOCK_CMD_BY_IDX.get(idx)
    if cmd is None:
        return
    _send_cmd_no_wait(f"{cmd}(0)")

def unlock_all_locks():
    """Best-effort unlock of all lockable buttons."""
    for i in range(5):
        unlock_button_idx(i)

def mask_manager_tick(selected_idx: int, aimbot_running: bool):
    """Manage button locks based on selected_idx and aimbot_running state."""
    
    global _mask_applied_idx

    if not is_connected:
        _mask_applied_idx = None
        return

    # clamp invalid index
    if not isinstance(selected_idx, int) or not (0 <= selected_idx <= 4):
        selected_idx = None

    if not aimbot_running:
        if _mask_applied_idx is not None:
            unlock_button_idx(_mask_applied_idx)
            _mask_applied_idx = None
        return

    # running: apply lock for selected_idx
    if selected_idx is None:
        # nothing selected -> make sure nothing is locked
        if _mask_applied_idx is not None:
            unlock_button_idx(_mask_applied_idx)
            _mask_applied_idx = None
        return

    if _mask_applied_idx != selected_idx:
        # switch lock to a new button
        if _mask_applied_idx is not None:
            unlock_button_idx(_mask_applied_idx)
        lock_button_idx(selected_idx)
        _mask_applied_idx = selected_idx

class Makcu:
    _instance = None
    _listener = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, port_name=None, baud_rate=115_200):
        if not hasattr(self, "_inited"):
            if not connect_to_makcu(port_name, baud_rate):
                print("[ERROR] MAKCU init failed to connect.")
            else:
                Makcu._listener = threading.Thread(target=listen_makcu, daemon=True)
                Makcu._listener.start()
            self._port_name = port_name
            self._baud_rate = baud_rate
            self._inited = True

    @property
    def connected(self):
        return is_connected and makcu is not None and makcu.is_open

    @property
    def port_name(self):
        return connected_port

    @property
    def baud_rate(self):
        return connected_baud

    def is_button_pressed(self, idx: int) -> bool:
        return is_button_pressed(idx)

    def move(self, x: float, y: float):
        if not is_connected:
            return
        dx, dy = int(x), int(y)
        with makcu_lock:
            makcu.write(f"km.move({dx},{dy})\r".encode())
            makcu.flush()

    def move_bezier(self, x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
        if not is_connected:
            return
        with makcu_lock:
            cmd = f"km.move({int(x)},{int(y)},{int(segments)},{int(ctrl_x)},{int(ctrl_y)})\r"
            makcu.write(cmd.encode())
            makcu.flush()

    def click(self):
        if not is_connected:
            return
        with makcu_lock:
            makcu.write(b"km.left(1)\r")
            makcu.flush()
            makcu.write(b"km.left(0)\r")
            makcu.flush()

    @staticmethod
    def mask_manager_tick(selected_idx: int, aimbot_running: bool):
        """Apply the selected MAKCU button mask state."""
        mask_manager_tick(selected_idx, aimbot_running)

    @staticmethod
    def cleanup():
        global is_connected, makcu, connected_port, connected_baud, _mask_applied_idx
        # Always release any locks before closing port
        try:
            unlock_all_locks()
        except Exception:
            pass
        _mask_applied_idx = None

        is_connected = False
        if makcu and makcu.is_open:
            makcu.close()
        makcu = None
        connected_port = None
        connected_baud = None
        Makcu._instance = None
        Makcu._listener = None
        print("[INFO] MAKCU serial cleaned up.")
