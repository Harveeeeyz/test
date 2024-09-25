from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import uic
import asyncio
import logging

logger = logging.getLogger(__name__)

class GroupCollectorTab(QWidget):
    log_message = pyqtSignal(str)

    def __init__(self, group_collector_controller, account_controller, loop):
        super().__init__()
        uic.loadUi('ui/group_collector_tab.ui', self)
        self.group_collector_controller = group_collector_controller
        self.account_controller = account_controller
        self.loop = loop
        self.init_ui()
        self.connect_signals()
        self.collected_groups = set()

    def init_ui(self):
        logger.debug("Initializing GroupCollectorTab UI")
        self.accountTableWidget.setColumnCount(3)
        self.accountTableWidget.setHorizontalHeaderLabels(['选择', '电话号码', '用户名'])
        self.groupTableWidget.setColumnCount(5)
        self.groupTableWidget.setHorizontalHeaderLabels(['选择', '群组名称', '群组链接', '群组ID', '成员数'])

    def connect_signals(self):
        logger.debug("Connecting signals in GroupCollectorTab")
        self.selectAllAccountsButton.clicked.connect(self.select_all_accounts)
        self.deselectAllAccountsButton.clicked.connect(self.deselect_all_accounts)
        self.addKeywordButton.clicked.connect(self.add_keyword)
        self.removeKeywordButton.clicked.connect(self.remove_keyword)
        self.startCollectionButton.clicked.connect(self.start_collection)

    def refresh_accounts(self):
        logger.debug("Refreshing accounts in GroupCollectorTab")
        self.accountTableWidget.setRowCount(0)
        for account in self.account_controller.get_all_accounts():
            row = self.accountTableWidget.rowCount()
            self.accountTableWidget.insertRow(row)
            checkbox = QCheckBox()
            self.accountTableWidget.setCellWidget(row, 0, checkbox)
            self.accountTableWidget.setItem(row, 1, QTableWidgetItem(account.phone))
            self.accountTableWidget.setItem(row, 2, QTableWidgetItem(account.first_name))

    def select_all_accounts(self):
        logger.debug("Selecting all accounts")
        for row in range(self.accountTableWidget.rowCount()):
            self.accountTableWidget.cellWidget(row, 0).setChecked(True)

    def deselect_all_accounts(self):
        logger.debug("Deselecting all accounts")
        for row in range(self.accountTableWidget.rowCount()):
            checkbox = self.accountTableWidget.cellWidget(row, 0)
            checkbox.setChecked(not checkbox.isChecked())

    def add_keyword(self):
        keyword = self.keywordInput.text().strip()
        if keyword:
            self.keywordList.addItem(keyword)
            self.keywordInput.clear()
            logger.debug(f"Added keyword: {keyword}")

    def remove_keyword(self):
        for item in self.keywordList.selectedItems():
            keyword = item.text()
            self.keywordList.takeItem(self.keywordList.row(item))
            logger.debug(f"Removed keyword: {keyword}")

    def start_collection(self):
        logger.info("Starting group collection process")
        self.log_message.emit("开始采集过程...")
        selected_accounts = []
        for row in range(self.accountTableWidget.rowCount()):
            if self.accountTableWidget.cellWidget(row, 0).isChecked():
                phone = self.accountTableWidget.item(row, 1).text()
                selected_accounts.append(phone)

        keywords = [self.keywordList.item(i).text() for i in range(self.keywordList.count())]

        if not selected_accounts:
            self.log_message.emit("请选择至少一个账号")
            logger.warning("No account selected")
            return

        if not keywords:
            self.log_message.emit("请添加至少一个关键词")
            logger.warning("No keyword added")
            return

        self.log_message.emit(f"选择了 {len(selected_accounts)} 个账号和 {len(keywords)} 个关键词")
        logger.info(f"Selected {len(selected_accounts)} accounts and {len(keywords)} keywords")
        self.groupTableWidget.setRowCount(0)
        self.collected_groups.clear()
        
        asyncio.run_coroutine_threadsafe(self.collect_groups(selected_accounts, keywords), self.loop)

    async def collect_groups(self, selected_accounts, keywords):
        try:
            async for result in self.group_collector_controller.collect_groups(selected_accounts, keywords):
                if isinstance(result, dict):
                    self.add_group_to_table(result)
                else:
                    self.log_message.emit(result)
                    logger.info(result)
        except Exception as e:
            error_msg = f"采集过程出错: {str(e)}"
            self.log_message.emit(error_msg)
            logger.error(error_msg, exc_info=True)
        
        self.log_message.emit("采集过程完成")
        logger.info("Group collection process completed")

    def add_group_to_table(self, group_info):
        logger.debug(f"Adding group to table: {group_info['name']}")
        self.group_collector_controller.add_collected_group(group_info)  # 添加到 GroupCollectorController
        row = self.groupTableWidget.rowCount()
        self.groupTableWidget.insertRow(row)
        checkbox = QCheckBox()
        self.groupTableWidget.setCellWidget(row, 0, checkbox)
        self.groupTableWidget.setItem(row, 1, QTableWidgetItem(group_info['name']))
        self.groupTableWidget.setItem(row, 2, QTableWidgetItem(group_info['link']))
        self.groupTableWidget.setItem(row, 3, QTableWidgetItem(str(group_info['id'])))
        self.groupTableWidget.setItem(row, 4, QTableWidgetItem(str(group_info['members']) if group_info['members'] is not None else "未知"))

        try:
            with open('group_links.txt', 'a', encoding='utf-8') as f:
                f.write(f"{group_info['name']},{group_info['link']},{group_info['id']},{group_info['members']}\n")
            logger.info(f"Added group to file: {group_info['name']}")
        except Exception as e:
            logger.error(f"Error writing to file: {str(e)}", exc_info=True)