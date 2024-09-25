from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import uic

class GroupCollectionTab(QWidget):
    log_message = pyqtSignal(str)

    def __init__(self, group_controller):
        super().__init__()
        uic.loadUi('ui/group_collection_tab.ui', self)
        self.group_controller = group_controller
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.groupTableWidget.setColumnCount(4)
        self.groupTableWidget.setHorizontalHeaderLabels(['选择', '群组名称', '群组ID', '成员数'])
        self.userActivityTableWidget.setColumnCount(4)
        self.userActivityTableWidget.setHorizontalHeaderLabels(['用户名', '姓名', '用户ID', '最近上线时间'])

    def connect_signals(self):
        self.retrieveGroupsButton.clicked.connect(self.on_retrieve_groups)
        self.startMonitoringButton.clicked.connect(self.start_monitoring)
        self.stopMonitoringButton.clicked.connect(self.group_controller.stop_monitoring)
        self.group_controller.group_info_retrieved.connect(self.update_group_table)
        self.group_controller.user_activity_detected.connect(self.update_user_activity_table)

    def on_retrieve_groups(self):
        self.log_message.emit("正在获取群组信息...")
        self.group_controller.retrieve_all_groups()

    def start_monitoring(self):
        selected_groups = []
        for row in range(self.groupTableWidget.rowCount()):
            checkbox = self.groupTableWidget.cellWidget(row, 0)
            if checkbox.isChecked():
                group_id = int(self.groupTableWidget.item(row, 2).text())
                selected_groups.append(group_id)
        if selected_groups:
            self.log_message.emit(f"开始监听 {len(selected_groups)} 个群组")
            self.group_controller.start_monitoring(selected_groups)
        else:
            self.log_message.emit("请先选择要监听的群组")

    def update_group_table(self, groups):
        self.log_message.emit(f"获取到 {len(groups)} 个群组")
        self.groupTableWidget.setRowCount(len(groups))
        for row, group in enumerate(groups):
            checkbox = QCheckBox()
            self.groupTableWidget.setCellWidget(row, 0, checkbox)
            self.groupTableWidget.setItem(row, 1, QTableWidgetItem(group['name']))
            self.groupTableWidget.setItem(row, 2, QTableWidgetItem(str(group['id'])))
            self.groupTableWidget.setItem(row, 3, QTableWidgetItem(str(group['members_count'])))

    def update_user_activity_table(self, user_info):
        self.log_message.emit(f"检测到新的用户活动: {user_info['name']}")
        row = self.userActivityTableWidget.rowCount()
        self.userActivityTableWidget.insertRow(row)
        self.userActivityTableWidget.setItem(row, 0, QTableWidgetItem(user_info['username']))
        self.userActivityTableWidget.setItem(row, 1, QTableWidgetItem(user_info['name']))
        self.userActivityTableWidget.setItem(row, 2, QTableWidgetItem(str(user_info['chat_id'])))
        self.userActivityTableWidget.setItem(row, 3, QTableWidgetItem(str(user_info['last_online'])))