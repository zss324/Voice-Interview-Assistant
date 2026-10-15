"""Load the Windows ICU shim before Qt DLL resolution in frozen builds."""

import ctypes
import os
from pathlib import Path

icu = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "icuuc.dll"
ctypes.WinDLL(str(icu))
