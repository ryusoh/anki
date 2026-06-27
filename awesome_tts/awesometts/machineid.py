"""
py-machineid
~~~~~~~~~~~~

Get the unique machine ID of any host (without admin privileges).

Basic usage:

    >>> import machineid
    >>> machineid.id()
    17A28A73-BEA9-4D4B-AF5B-03A5AAE9B92C

You can anonymize the ID like so, with an optional app ID:

    >>> machineid.hashed_id('myappid')
    366048092ef4e7db53cd7adec82dcab15ab67ac2a6b234dc6a69303a4dd48e83
    >>> machineid.hashed_id()
    ce2127ade536eaa9529f4a7b73141bbc2f094c46e32742c97679e186e7f13fde

Special thanks to Denis Brodbeck for his Go package, machineid (https://github.com/denisbrodbeck/machineid).

:license: MIT, see LICENSE for more details.
"""

__version__ = '0.7.0'
__author__ = 'Zeke Gabrielse'
__credits__ = 'https://github.com/denisbrodbeck/machineid'

import hashlib
import hmac
import re
import subprocess
from platform import uname
from sys import platform

try:
    import winregistry as winregistry_lib
except ImportError:
    winregistry_lib = None
import logging
from typing import Optional


class MachineIdNotFound(RuntimeError):
    """
    Raised when this library is unable to determine the machine id for the
    system where it is running.
    """


def __sanitize__(id: str) -> str:
    return re.sub(r'[\x00-\x1f\x7f-\x9f\s]', '', id).strip()


def __exec__(cmd: list) -> Optional[str]:
    try:
        return subprocess.run(
            cmd, shell=False, capture_output=True, check=True, encoding='utf-8'
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None


def __read__(path: str) -> Optional[str]:
    try:
        with open(path) as f:
            return f.read().strip()
    except IOError:
        return None


def __reg__(key_name: str, value_name: str) -> Optional[str]:
    if winregistry_lib is None:
        return None
    try:
        with winregistry_lib.open_value(key_name, value_name) as reg:
            if reg.data and isinstance(reg.data, str):
                return reg.data.strip()
    except OSError:
        logging.getLogger(__name__).warning("Failed to read machineid from registry.")
    return None


def _get_id_darwin() -> Optional[str]:
    out = __exec__(["ioreg", "-d2", "-c", "IOPlatformExpertDevice"])
    if out:
        for line in out.splitlines():
            if "IOPlatformUUID" in line:
                parts = line.split('"')
                if len(parts) >= 2:
                    return parts[-2]
    return None


def _get_id_win32(winregistry: bool) -> Optional[str]:
    id = None
    if winregistry:
        id = __reg__(r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography', 'MachineGuid')
    else:
        id = __exec__(
            [
                "powershell.exe",
                "-ExecutionPolicy",
                "bypass",
                "-command",
                "(Get-CimInstance -Class Win32_ComputerSystemProduct).UUID",
            ]
        )
    if not id:
        out = __exec__(["wmic", "csproduct", "get", "uuid"])
        if out:
            id = out.split('\n')[2].strip()
    return id


def _get_id_linux() -> Optional[str]:
    id = __read__('/var/lib/dbus/machine-id')
    if not id:
        id = __read__('/etc/machine-id')
    if not id:
        cgroup = __read__('/proc/self/cgroup')
        if cgroup and 'docker' in cgroup:
            lines = cgroup.splitlines()
            if lines:
                parts = lines[0].split('/')
                if len(parts) >= 3:
                    id = parts[2]
    if not id:
        mountinfo = __read__('/proc/self/mountinfo')
        if mountinfo and 'docker' in mountinfo:
            match = re.search(r'docker/containers/([a-f0-9]+)/hostname', mountinfo)
            if match:
                id = match.group(1)
    if not id and 'microsoft' in uname().release:  # wsl
        id = __exec__(
            [
                "powershell.exe",
                "-ExecutionPolicy",
                "bypass",
                "-command",
                "(Get-CimInstance -Class Win32_ComputerSystemProduct).UUID",
            ]
        )
    return id


def _get_id_bsd() -> Optional[str]:
    id = __read__('/etc/hostid')
    if not id:
        id = __exec__(["kenv", "-q", "smbios.system.uuid"])
    return id


def id(winregistry: bool = True) -> str:
    """
    id returns the platform specific device GUID of the current host OS.
    """

    id = None
    if platform == 'darwin':
        id = _get_id_darwin()
    elif platform in ('win32', 'cygwin', 'msys'):
        id = _get_id_win32(winregistry)
    elif platform.startswith('linux'):
        id = _get_id_linux()
    elif platform.startswith(('openbsd', 'freebsd')):
        id = _get_id_bsd()

    if not id:
        raise MachineIdNotFound('failed to obtain id on platform {}'.format(platform))

    return __sanitize__(id)


def hashed_id(app_id: str = '', **kwargs) -> str:
    """
    hashed_id returns the device's native GUID, hashed using HMAC-SHA256 with
    an optional application ID.
    """

    return hmac.new(bytes(app_id.encode()), id(**kwargs).encode(), hashlib.sha256).hexdigest()
