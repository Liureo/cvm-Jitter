import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


APP_NAME = "cvm Jitter"
APP_ICON = Path(__file__).resolve().parent / "app" / "ui" / "icon" / "cvm.jpg"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("CVM-AI")
    app_icon = QIcon(str(APP_ICON))
    app.setWindowIcon(app_icon)
    installed_fonts = set(QFontDatabase.families())
    for family in ("Microsoft JhengHei UI", "Microsoft JhengHei", "Noto Sans CJK TC"):
        if family in installed_fonts:
            app.setFont(QFont(family, 10))
            break

    window = MainWindow()
    window.setWindowIcon(app_icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
