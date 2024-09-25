import os
import asyncio
from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QFileDialog, QCheckBox, QListWidgetItem, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QListWidget, QTabWidget, QTableWidget
from PyQt6.QtCore import Qt, pyqtSignal

class GroupManagerTab(QWidget):
    log_message = pyqtSignal(str)

    def __init__(self, account_controller, group_collector_controller):
        super().__init__()
        self.account_controller = account_controller
        self.group_collector_controller = group_collector_controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_join_group_tab(), "加群")
        self.tab_widget.addTab(self.create_send_message_tab(), "群发消息")
        layout.addWidget(self.tab_widget)

        self.setLayout(layout)

    def create_send_message_tab(self):
        tab = QWidget()
        layout = QHBoxLayout()

        # 左侧布局：消息编辑和账号列表
        left_layout = QVBoxLayout()
        
        # 账号列表
        account_layout = QVBoxLayout()
        account_layout.addWidget(QLabel("账号列表"))
        self.sendAccountTableWidget = QTableWidget()
        self.sendAccountTableWidget.setColumnCount(2)
        self.sendAccountTableWidget.setHorizontalHeaderLabels(["选择", "账号"])
        account_layout.addWidget(self.sendAccountTableWidget)
        left_layout.addLayout(account_layout)

        # 消息编辑和列表
        message_layout = QVBoxLayout()
        self.messageInput = QTextEdit()
        message_layout.addWidget(self.messageInput)

        button_layout = QHBoxLayout()
        self.addMessageButton = QPushButton("添加消息")
        self.addMessageButton.clicked.connect(self.add_message)
        button_layout.addWidget(self.addMessageButton)

        self.uploadFileButton = QPushButton("上传文件")
        self.uploadFileButton.clicked.connect(self.upload_file)
        button_layout.addWidget(self.uploadFileButton)

        self.deleteMessageButton = QPushButton("删除消息")
        self.deleteMessageButton.clicked.connect(self.delete_selected_message)
        button_layout.addWidget(self.deleteMessageButton)

        message_layout.addLayout(button_layout)

        self.messageList = QListWidget()
        self.messageList.itemDoubleClicked.connect(self.delete_selected_message)
        message_layout.addWidget(self.messageList)

        left_layout.addLayout(message_layout)

        layout.addLayout(left_layout)

        # 右侧布局：群组列表
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("群组列表"))
        self.sendGroupTableWidget = QTableWidget()
        self.sendGroupTableWidget.setColumnCount(3)
        self.sendGroupTableWidget.setHorizontalHeaderLabels(["选择", "群组名称", "群组ID"])
        right_layout.addWidget(self.sendGroupTableWidget)

        # 发送消息按钮
        send_button = QPushButton("发送消息")
        send_button.clicked.connect(self.send_messages_to_selected_groups)
        right_layout.addWidget(send_button)

        layout.addLayout(right_layout)

        tab.setLayout(layout)
        return tab

    def create_join_group_tab(self):
        tab = QWidget()
        layout = QHBoxLayout()

        # 账号列表
        account_layout = QVBoxLayout()
        account_layout.addWidget(QLabel("账号列表"))
        self.accountTableWidget = QTableWidget()
        self.accountTableWidget.setColumnCount(2)
        self.accountTableWidget.setHorizontalHeaderLabels(["选择", "账号"])
        account_layout.addWidget(self.accountTableWidget)
        layout.addLayout(account_layout)

        # 群组列表
        group_layout = QVBoxLayout()
        group_layout.addWidget(QLabel("群组列表"))
        self.groupTableWidget = QTableWidget()
        self.groupTableWidget.setColumnCount(4)
        self.groupTableWidget.setHorizontalHeaderLabels(["选择", "群组名称", "群组ID", "链接"])
        group_layout.addWidget(self.groupTableWidget)
        layout.addLayout(group_layout)

        # 加群按钮
        join_button = QPushButton("加入选中群组")
        join_button.clicked.connect(self.join_selected_groups)
        layout.addWidget(join_button)

        tab.setLayout(layout)
        return tab

    def add_message(self):
        message = self.messageInput.toPlainText()
        if message:
            self.messageList.addItem(message)
            self.messageInput.clear()

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "All Files (*);;Audio Files (*.ogg *.mp3);;Images (*.png *.jpg);;Videos (*.mp4)")
        if file_path:
            file_name = os.path.basename(file_path)
            item = QListWidgetItem(f"[File] {file_path}")  # 保存完整路径
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.messageList.addItem(item)
            self.log_message.emit(f"文件已上传: {file_name}")

    def delete_selected_message(self):
        current_item = self.messageList.currentItem()
        if current_item:
            row = self.messageList.row(current_item)
            self.messageList.takeItem(row)
            self.log_message.emit(f"消息已删除: {current_item.text()}")

    def refresh_accounts(self):
        self.accountTableWidget.setRowCount(0)
        for account in self.account_controller.get_all_accounts():
            row = self.accountTableWidget.rowCount()
            self.accountTableWidget.insertRow(row)
            checkbox = QCheckBox()
            self.accountTableWidget.setCellWidget(row, 0, checkbox)
            self.accountTableWidget.setItem(row, 1, QTableWidgetItem(account.phone))

        self.sendAccountTableWidget.setRowCount(0)
        for account in self.account_controller.get_all_accounts():
            row = self.sendAccountTableWidget.rowCount()
            self.sendAccountTableWidget.insertRow(row)
            checkbox = QCheckBox()
            self.sendAccountTableWidget.setCellWidget(row, 0, checkbox)
            self.sendAccountTableWidget.setItem(row, 1, QTableWidgetItem(account.phone))

    def refresh_groups(self):
        groups = self.group_collector_controller.get_collected_groups()
        self.groupTableWidget.setRowCount(0)
        self.sendGroupTableWidget.setRowCount(0)
        for group in groups:
            self.add_group_to_tables(group)

    def add_group_to_tables(self, group):
        # 加群表格
        row = self.groupTableWidget.rowCount()
        self.groupTableWidget.insertRow(row)
        checkbox1 = QCheckBox()
        self.groupTableWidget.setCellWidget(row, 0, checkbox1)
        self.groupTableWidget.setItem(row, 1, QTableWidgetItem(group.get('name', '')))
        self.groupTableWidget.setItem(row, 2, QTableWidgetItem(str(group.get('id', ''))))
        self.groupTableWidget.setItem(row, 3, QTableWidgetItem(group.get('link', '')))
        
        # 群发表格
        row = self.sendGroupTableWidget.rowCount()
        self.sendGroupTableWidget.insertRow(row)
        checkbox2 = QCheckBox()
        self.sendGroupTableWidget.setCellWidget(row, 0, checkbox2)
        self.sendGroupTableWidget.setItem(row, 1, QTableWidgetItem(group.get('name', '')))
        self.sendGroupTableWidget.setItem(row, 2, QTableWidgetItem(str(group.get('id', ''))))

    def refresh_data(self):
        self.refresh_accounts()
        self.refresh_groups()

    def get_selected_items(self, table_widget):
        selected_items = []
        for row in range(table_widget.rowCount()):
            if table_widget.cellWidget(row, 0).isChecked():
                item_data = [table_widget.item(row, i).text() for i in range(1, table_widget.columnCount())]
                selected_items.append(item_data)
        return selected_items

    def join_selected_groups(self):
        selected_accounts = self.get_selected_items(self.accountTableWidget)
        selected_groups = self.get_selected_items(self.groupTableWidget)
        asyncio.create_task(self.join_groups(selected_accounts, selected_groups))

    async def join_groups(self, selected_accounts, selected_groups):
        for account in selected_accounts:
            for group in selected_groups:
                try:
                    worker = self.account_controller.workers.get(account[0])
                    if worker and worker.client:
                        await worker.client(JoinChannelRequest(group[2]))  # Assuming the link is in the third column
                        self.log_message.emit(f"账号 {account[0]} 成功加入群组 {group[0]}")
                    else:
                        self.log_message.emit(f"账号 {account[0]} 未找到客户端，无法加入群组 {group[0]}")
                except Exception as e:
                    self.log_message.emit(f"账号 {account[0]} 加入群组 {group[0]} 失败: {str(e)}")

    def send_messages_to_selected_groups(self):
        messages = [self.messageList.item(i).text() for i in range(self.messageList.count())]
        selected_groups = self.get_selected_items(self.sendGroupTableWidget)
        selected_accounts = self.get_selected_items(self.sendAccountTableWidget)
        
        if not selected_accounts:
            self.log_message.emit("请选择至少一个账号进行发送")
            return

        for account in selected_accounts:
            asyncio.create_task(self.send_messages(messages, selected_groups, account[0]))

    async def send_messages(self, messages, selected_groups, account):
        worker = self.account_controller.workers.get(account)
        if not worker or not worker.client:
            self.log_message.emit(f"账号 {account} 未找到客户端，无法发送消息")
            return

        for group in selected_groups:
            try:
                group_name = group[0]
                group_id = int(group[1])
                entity = await worker.client.get_entity(group_id)
                
                for message in messages:
                    if message.startswith('[File]'):
                        file_path = message[6:].strip()
                        if os.path.exists(file_path):
                            try:
                                await worker.client.send_file(entity, file_path)
                                self.log_message.emit(f"文件 {os.path.basename(file_path)} 成功发送到群组 {group_name} (账号: {account})")
                            except Exception as e:
                                self.log_message.emit(f"发送文件 {os.path.basename(file_path)} 到群组 {group_name} 失败 (账号: {account}): {str(e)}")
                        else:
                            self.log_message.emit(f"文件不存在: {file_path}")
                    else:
                        await worker.client.send_message(entity, message)
                
                self.log_message.emit(f"成功发送消息到群组 {group_name} (账号: {account})")
            except Exception as e:
                self.log_message.emit(f"发送消息到群组 {group_name} 失败 (账号: {account}): {str(e)}")

    def get_default_account(self):
        accounts = self.account_controller.get_all_accounts()
        return accounts[0].phone if accounts else None
        
    def refresh_joined_groups(self):
        for account in self.account_controller.get_all_accounts():
            asyncio.create_task(self._fetch_and_display_joined_groups(account.phone))

    async def _fetch_and_display_joined_groups(self, account):
        joined_groups = await self.group_collector_controller.get_joined_groups(account)
        for group in joined_groups:
            self.add_group_to_tables(group)
