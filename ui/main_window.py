import logging
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QApplication
from PyQt6 import uic
from controllers.account_controller import AccountController
from controllers.group_controller import GroupController
from controllers.group_collector_controller import GroupCollectorController
from ui.account_tab import AccountTab
from ui.group_collection_tab import GroupCollectionTab
from ui.group_collector_tab import GroupCollectorTab
from ui.group_manager_tab import GroupManagerTab  # 更改为 GroupManagerTab
import asyncio

logger = logging.getLogger(__name__)

class TelegramAccountCenter(QMainWindow):
    def __init__(self, loop):
        super().__init__()
        uic.loadUi('ui/main_window.ui', self)
        
        self.loop = loop
        self.account_controller = AccountController(self.loop)
        self.group_controller = GroupController(self.account_controller)
        self.group_collector_controller = GroupCollectorController(self.account_controller)
        
        self.setup_logging()
        self.init_ui()

    def setup_logging(self):
        logging.basicConfig(level=logging.DEBUG)
        self.log_handler = logging.StreamHandler()
        self.log_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.log_handler.setFormatter(formatter)
        logger.addHandler(self.log_handler)

    def init_ui(self):
        logger.debug("Initializing UI")
        self.account_tab = AccountTab(self.account_controller)
        self.group_collection_tab = GroupCollectionTab(self.group_controller)
        self.group_collector_tab = GroupCollectorTab(self.group_collector_controller, self.account_controller, self.loop)
        self.group_manager_tab = GroupManagerTab(self.account_controller, self.group_collector_controller)
        
        if not hasattr(self, 'tabWidget'):
            self.tabWidget = QTabWidget(self)
            self.centralWidget().layout().addWidget(self.tabWidget)
        
        self.tabWidget.addTab(self.account_tab, "账号中心")
        self.tabWidget.addTab(self.group_collection_tab, "用户/群组采集")
        self.tabWidget.addTab(self.group_collector_tab, "群组搜集器")
        self.tabWidget.addTab(self.group_manager_tab, "群组管理器")  # 添加新的标签页
        
        self.account_tab.log_message.connect(self.log_message)
        self.group_collection_tab.log_message.connect(self.log_message)
        self.group_collector_tab.log_message.connect(self.log_message)
        self.group_manager_tab.log_message.connect(self.log_message)  # 连接新标签页的日志信号

        self.account_tab.account_added.connect(self.update_all_account_lists)
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        self.account_controller.load_api_credentials()  # 修复缩进
        self.update_all_account_lists()  # 修复缩进
        logger.debug("UI initialization completed")

    def log_message(self, message):
        logger.info(message)
        if hasattr(self, 'logTextEdit'):
            self.logTextEdit.append(message)
        else:
            print(message)

    def update_all_account_lists(self):
        logger.debug("Updating all account lists")
        self.account_tab.refresh_table()
        if hasattr(self.group_collection_tab, 'refresh_accounts'):
            self.group_collection_tab.refresh_accounts()
        self.group_collector_tab.refresh_accounts()
        self.group_manager_tab.refresh_accounts()  # 刷新群组管理器的账号列表

    def on_tab_changed(self, index):
        logger.debug(f"Tab changed to index {index}")
        if self.tabWidget.tabText(index) == "群组管理器":
            self.group_manager_tab.refresh_data()
            self.group_manager_tab.refresh_joined_groups()

    def closeEvent(self, event):
        logger.debug("Close event triggered")
        self.account_controller.stop_all_workers()
        super().closeEvent(event)
