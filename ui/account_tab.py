from PyQt6.QtWidgets import (
    QWidget, QTableWidgetItem, QFileDialog, QInputDialog, QMessageBox,
    QLineEdit, QPushButton, QCheckBox, QTableWidget
)
from PyQt6.QtCore import pyqtSignal
from PyQt6 import uic
from utils.validators import validate_phone_number
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

class AccountTab(QWidget):
    log_message = pyqtSignal(str)
    account_added = pyqtSignal()

    def __init__(self, account_controller, parent=None):
        super().__init__(parent)
        uic.loadUi('ui/account_tab.ui', self)
        self.account_controller = account_controller
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setHorizontalHeaderLabels(['账号', '姓', '名', '账号ID', '状态', '手机号', '群发状态'])
        self.init_ui()
        self.refresh_table()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjustLayout()

    def adjustLayout(self):
        width = self.width()
        height = self.height()
        
        # 调整表格大小
        self.tableWidget.setGeometry(10, 10, width - 20, height // 2 - 20)
        
        # 调整登录和修改信息组框的大小和位置
        group_height = height // 2 - 30
        self.groupBox.setGeometry(10, height // 2 + 10, width // 2 - 15, group_height)
        self.groupBox_2.setGeometry(width // 2 + 5, height // 2 + 10, width // 2 - 15, group_height)
        
    def init_ui(self):
        """初始化UI组件并连接信号和槽"""
        self.pushButtonSendCode.clicked.connect(self.safe_send_code)
        self.pushButtonCodeLogin.clicked.connect(self.safe_login)
        self.pushButtonSessionLogin.clicked.connect(self.session_login)
        self.pushButtonUpdateProfile.clicked.connect(self.update_profile)

        # 初始化控件
        self.lineEditPhone = self.findChild(QLineEdit, 'lineEditPhone')
        self.lineEditCode = self.findChild(QLineEdit, 'lineEditCode')
        self.lineEditApiId = self.findChild(QLineEdit, 'lineEditApiId')
        self.lineEditApiHash = self.findChild(QLineEdit, 'lineEditApiHash')
        self.lineEditTwoFaPassword = self.findChild(QLineEdit, 'lineEditTwoFaPassword')
        self.pushButtonSendCode = self.findChild(QPushButton, 'pushButtonSendCode')
        self.pushButtonCodeLogin = self.findChild(QPushButton, 'pushButtonCodeLogin')
        self.pushButtonSessionLogin = self.findChild(QPushButton, 'pushButtonSessionLogin')
        self.pushButtonUpdateProfile = self.findChild(QPushButton, 'pushButtonUpdateProfile')
        self.tableWidget = self.findChild(QTableWidget, 'tableWidget')

        # 资料更新控件
        self.checkBoxModifyNickname = self.findChild(QCheckBox, 'checkBoxModifyNickname')
        self.checkBoxModifyLastName = self.findChild(QCheckBox, 'checkBoxModifyLastName')
        self.checkBoxModifyAbout = self.findChild(QCheckBox, 'checkBoxModifyAbout')
        self.checkBoxModifyAvatar = self.findChild(QCheckBox, 'checkBoxModifyAvatar')
        self.lineEditFirstName = self.findChild(QLineEdit, 'lineEditFirstName')
        self.lineEditLastName = self.findChild(QLineEdit, 'lineEditLastName')
        self.lineEditAbout = self.findChild(QLineEdit, 'lineEditAbout')

    def update_account_status(self, phone, first_name, last_name, user_id, is_banned, phone_number):
        """更新表格中指定账号的状态"""
        for row in range(self.tableWidget.rowCount()):
            if self.tableWidget.item(row, 0).text() == phone:
                self.tableWidget.setItem(row, 0, QTableWidgetItem(phone))
                self.tableWidget.setItem(row, 1, QTableWidgetItem(last_name))
                self.tableWidget.setItem(row, 2, QTableWidgetItem(first_name))
                self.tableWidget.setItem(row, 3, QTableWidgetItem(str(user_id)))
                self.tableWidget.setItem(row, 4, QTableWidgetItem("已封禁" if is_banned else "正常"))
                self.tableWidget.setItem(row, 5, QTableWidgetItem(phone_number))
                self.tableWidget.setItem(row, 6, QTableWidgetItem("未群发"))
                self.log_message.emit(f"账号 {phone} ({first_name} {last_name}) 登录成功，状态：{'已封禁' if is_banned else '正常'}")
                return
        
        self.add_account_to_table(phone, first_name, last_name, user_id, is_banned, phone_number)

    def safe_send_code(self):
        try:
            phone = self.lineEditPhone.text()
            api_id = self.lineEditApiId.text()
            api_hash = self.lineEditApiHash.text()
            two_fa_password = self.lineEditTwoFaPassword.text()

            if not phone or not api_id or not api_hash:
                self.log_message.emit("请填写电话号码、API ID和API Hash")
                return

            if not validate_phone_number(phone):
                self.log_message.emit("无效的电话号码格式。请使用国际格式，例如：+8529420xxxx")
                return

            worker = self.account_controller.create_worker(phone, int(api_id), api_hash, two_fa_password)
            worker.log_message.connect(self.log_message.emit)
            worker.login_success.connect(self.add_account_to_table)
            worker.error_occurred.connect(self.log_message.emit)
            worker.client_ready.connect(lambda: asyncio.create_task(self.account_controller.send_code(phone)))
            asyncio.create_task(self.account_controller.start_worker(phone))
        except Exception as e:
            self.log_message.emit(f"发送验证码时出错: {str(e)}")

    def safe_login(self):
        """安全登录"""
        try:
            phone = self.lineEditPhone.text()
            code = self.lineEditCode.text()
            two_fa_password = self.lineEditTwoFaPassword.text()
            asyncio.create_task(self.account_controller.login(phone, code, two_fa_password))
        except Exception as e:
            self.log_message.emit(f"登录时出错: {str(e)}")

    def session_login(self):
        """选择登录方式：批量或单个账号"""
        reply = QMessageBox.question(self, '登录方式', 
                                     "是否要批量登录所有账号？",
                                     QMessageBox.StandardButton.Yes | 
                                     QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            # 批量登录所有账号
            asyncio.create_task(self.batch_login())
        else:
            # 单个账号登录
            session_file, _ = QFileDialog.getOpenFileName(self, "选择Session文件", "", "Session Files (*.session)")
            if session_file:
                asyncio.create_task(self.single_login(session_file))

    def update_profile(self):
        """更新选定账号的资料"""
        selected_rows = self.tableWidget.selectionModel().selectedRows()
        if not selected_rows:
            self.log_message.emit("请先选择要修改的账号")
            return

        first_name = self.lineEditFirstName.text() if self.checkBoxModifyNickname.isChecked() else None
        last_name = self.lineEditLastName.text() if self.checkBoxModifyLastName.isChecked() else None
        about = self.lineEditAbout.text() if self.checkBoxModifyAbout.isChecked() else None
        photo_path = None
        if self.checkBoxModifyAvatar.isChecked():
            photo_path, _ = QFileDialog.getOpenFileName(self, "选择头像", "", "Image Files (*.png *.jpg *.bmp)")

        for row in selected_rows:
            phone = self.tableWidget.item(row.row(), 0).text()
            asyncio.create_task(self.account_controller.update_profile(phone, first_name, last_name, about, photo_path))

    def add_account_to_table(self, phone, first_name, last_name, user_id, is_banned, phone_number):
        """将账户添加到表格中"""
        logger.info(f"Adding account to table: {phone}")
        row_position = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_position)
        self.tableWidget.setItem(row_position, 0, QTableWidgetItem(phone))
        self.tableWidget.setItem(row_position, 1, QTableWidgetItem(last_name))
        self.tableWidget.setItem(row_position, 2, QTableWidgetItem(first_name))
        self.tableWidget.setItem(row_position, 3, QTableWidgetItem(str(user_id)))
        self.tableWidget.setItem(row_position, 4, QTableWidgetItem("已封禁" if is_banned else "正常"))
        self.tableWidget.setItem(row_position, 5, QTableWidgetItem(phone_number))
        self.tableWidget.setItem(row_position, 6, QTableWidgetItem("未群发"))
        self.account_controller.add_account(phone, first_name, last_name, user_id, is_banned, phone_number)
        self.refresh_table()

    def refresh_table(self):
        """刷新表格数据"""
        logger.info("Refreshing account table")
        self.tableWidget.setRowCount(0)
        for account in self.account_controller.get_all_accounts():
            row_position = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row_position)
            self.tableWidget.setItem(row_position, 0, QTableWidgetItem(account.phone))
            self.tableWidget.setItem(row_position, 1, QTableWidgetItem(account.last_name))
            self.tableWidget.setItem(row_position, 2, QTableWidgetItem(account.first_name))
            self.tableWidget.setItem(row_position, 3, QTableWidgetItem(account.user_id))
            self.tableWidget.setItem(row_position, 4, QTableWidgetItem("已封禁" if account.is_banned else "正常"))
            self.tableWidget.setItem(row_position, 5, QTableWidgetItem(account.phone_number))
            self.tableWidget.setItem(row_position, 6, QTableWidgetItem("未群发" if not account.message_sent else "已群发"))

    async def batch_login(self):
        """批量登录所有账号"""
        results = await self.account_controller.session_login()
        for result in results:
            self.log_message.emit(result)

    async def single_login(self, session_file):
        """单个账号登录"""
        result = await self.account_controller.session_login(session_file)
        self.log_message.emit(result)
        self.refresh_table()
