import sys
import os
import traceback

# Cài exception hook TRƯỚC KHI import bất cứ thứ gì
_log_path = os.path.join(os.path.dirname(__file__), "..", "error_log.txt")

def _excepthook(exc_type, exc_value, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        with open(_log_path, "w", encoding="utf-8") as f:
            f.write(msg)
    except Exception:
        pass
    print(msg, file=sys.__stderr__)

sys.excepthook = _excepthook

sys.path.insert(0, os.path.dirname(__file__))

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
except Exception:
    _excepthook(*sys.exc_info())
    sys.exit(1)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GeoDraw")

    try:
        app.setAttribute(
            Qt.ApplicationAttribute.AA_SynthesizeMouseForUnhandledTabletEvents, False)
    except AttributeError:
        pass  # attribute không tồn tại trong một số phiên bản PyQt6

    from ui.main_window import MainWindow
    win = MainWindow()
    win.show()
    return app.exec()


def _close_terminal():
    """Đóng cửa sổ terminal đang chạy script này."""
    try:
        import platform, subprocess
        if platform.system() == "Windows":
            ppid = os.getppid()   # PID của shell (cmd / PowerShell)
            # Dùng taskkill trong tiến trình con riêng (không tạo cửa sổ mới)
            # timeout 1 giây để Python kịp thoát hoàn toàn trước khi shell bị kill
            subprocess.Popen(
                f"cmd /c timeout /t 1 /nobreak >nul & taskkill /f /pid {ppid}",
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            # Linux / macOS: gửi SIGHUP cho process group của terminal
            import signal
            os.killpg(os.getpgid(os.getpid()), signal.SIGHUP)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        _excepthook(*sys.exc_info())
        code = 1
    finally:
        _close_terminal()
        sys.exit(code)
