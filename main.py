import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import TelegramAccountCenter
import asyncio
import qasync
import logging

# 设置根日志记录器
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

def exception_hook(exctype, value, traceback):
    logger.error("Uncaught exception", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)
    sys.exit(1)

def main():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = TelegramAccountCenter(loop)
    window.show()

    sys.excepthook = exception_hook

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()