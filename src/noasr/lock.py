"""Single-instance lock to prevent multiple noasr processes."""

import os
from contextlib import suppress
from pathlib import Path
from typing import Optional

from noasr.constants import LOCK_FILENAME


class SingleInstanceLock:
    """
    Cross-platform single-instance lock using file-based locking.

    On Windows: Uses msvcrt file locking with PID tracking.
    On Unix: Uses fcntl file locking with PID tracking.
    """

    def __init__(self, lock_path: Optional[Path] = None) -> None:
        """Initialize the single instance lock."""
        if lock_path is None:
            from noasr.config import DEFAULT_CONFIG_DIR

            lock_path = DEFAULT_CONFIG_DIR / LOCK_FILENAME

        self._lock_path = lock_path
        self._lock_file: Optional[int] = None
        self._owned = False

    def acquire(self) -> bool:
        """
        Attempt to acquire the single-instance lock.

        Returns:
            True if lock acquired (first instance), False otherwise.
        """
        if self._owned:
            return True

        lock_dir = self._lock_path.parent
        lock_dir.mkdir(parents=True, exist_ok=True)

        try:
            if os.name == "nt":
                return self._acquire_windows()
            else:
                return self._acquire_unix()
        except Exception:
            return False

    def _acquire_windows(self) -> bool:
        """Acquire lock on Windows using msvcrt file locking."""
        import msvcrt

        try:
            # Create or open lock file
            self._lock_file = os.open(
                str(self._lock_path),
                os.O_CREAT | os.O_RDWR,
            )

            # Try to lock the file (non-blocking)
            try:
                msvcrt.locking(self._lock_file, msvcrt.LK_NBLCK, 1)
                # If successful, unlock and relock as shared lock to keep it locked
                msvcrt.locking(self._lock_file, msvcrt.LK_UNLCK, 1)
                msvcrt.locking(self._lock_file, msvcrt.LK_LOCK, 1)
                self._write_pid()
                self._owned = True
                return True
            except OSError:
                # Lock is held by another process
                os.close(self._lock_file)
                self._lock_file = None
                return False
        except Exception:
            if self._lock_file is not None:
                os.close(self._lock_file)
                self._lock_file = None
            return False

    def _acquire_unix(self) -> bool:
        """Acquire lock on Unix using fcntl file locking."""
        try:
            import fcntl

            self._lock_file = os.open(str(self._lock_path), os.O_CREAT | os.O_RDWR)

            try:
                fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._write_pid()
                self._owned = True
                return True
            except OSError:
                os.close(self._lock_file)
                self._lock_file = None
                return False
        except ImportError:
            return self._fallback_acquire()

    def _fallback_acquire(self) -> bool:
        """Fallback lock using PID file check."""
        if self._lock_path.exists():
            try:
                pid = int(self._lock_path.read_text(encoding="utf-8").strip())
                # Check if process is still running
                if self._is_process_running(pid):
                    return False
            except (ValueError, OSError):
                # Invalid PID file, assume stale
                pass

        # Try to create lock file atomically
        try:
            fd = os.open(str(self._lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as f:
                f.write(str(os.getpid()))
            self._owned = True
            return True
        except FileExistsError:
            return False

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running."""
        if os.name == "nt":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, 0, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

    def release(self) -> None:
        """Release the single-instance lock."""
        if not self._owned:
            return

        try:
            if self._lock_file is not None:
                if os.name == "nt":
                    import msvcrt

                    with suppress(OSError):
                        msvcrt.locking(self._lock_file, msvcrt.LK_UNLCK, 1)
                else:
                    with suppress(OSError):
                        import fcntl

                        fcntl.flock(self._lock_file, fcntl.LOCK_UN)
                with suppress(OSError):
                    os.close(self._lock_file)
                self._lock_file = None

            # Remove lock file
            with suppress(OSError):
                if self._lock_path.exists():
                    self._lock_path.unlink()
        finally:
            self._owned = False

    def is_owned(self) -> bool:
        """Check if this instance currently owns the lock."""
        return self._owned

    def _write_pid(self) -> None:
        """Write current PID to lock file."""
        if self._lock_file is not None:
            with suppress(OSError):
                os.lseek(self._lock_file, 0, os.SEEK_SET)
                os.write(self._lock_file, str(os.getpid()).encode())

    def __enter__(self) -> "SingleInstanceLock":
        """Context manager entry."""
        if not self.acquire():
            raise SingleInstanceError(
                "Another instance of noasr is already running. "
                "Only one instance can run at a time to prevent hotkey conflicts."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.release()


class SingleInstanceError(Exception):
    """Raised when another instance is already running."""

    pass


# Global runtime lock instance
_runtime_lock: Optional[SingleInstanceLock] = None


def get_runtime_lock() -> SingleInstanceLock:
    """Get the global runtime lock instance."""
    global _runtime_lock
    if _runtime_lock is None:
        _runtime_lock = SingleInstanceLock()
    return _runtime_lock


def acquire_runtime_lock() -> bool:
    """Acquire the global runtime lock."""
    return get_runtime_lock().acquire()


def release_runtime_lock() -> None:
    """Release the global runtime lock."""
    global _runtime_lock
    if _runtime_lock is not None:
        _runtime_lock.release()
        _runtime_lock = None
