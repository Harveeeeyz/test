from PyQt6.QtCore import QObject, pyqtSignal
from telethon import TelegramClient, events
from telethon.tl.types import Channel, User
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import UserStatusOnline, UserStatusOffline, UserStatusRecently, UserStatusLastWeek, UserStatusLastMonth

class GroupController(QObject):
    group_info_retrieved = pyqtSignal(list)
    user_activity_detected = pyqtSignal(dict)
    log_message = pyqtSignal(str)

    def __init__(self, account_controller):
        super().__init__()
        self.account_controller = account_controller
        self.monitored_groups = set()

    async def get_group_info(self, client):
        groups = []
        async for dialog in client.iter_dialogs():
            if isinstance(dialog.entity, Channel) and dialog.is_group:
                try:
                    full_chat = await client(GetFullChannelRequest(dialog.entity))
                    groups.append({
                        'name': dialog.name,
                        'id': dialog.id,
                        'members_count': full_chat.full_chat.participants_count
                    })
                except Exception as e:
                    self.log_message.emit(f"获取群组 {dialog.name} 信息时出错: {str(e)}")
        return groups

    def retrieve_all_groups(self):
        self.log_message.emit("开始从所有账号获取群组信息")
        for phone, worker in self.account_controller.workers.items():
            if worker.client and worker.client.is_connected():
                worker.loop.create_task(self._retrieve_groups(worker.client, phone))
            else:
                self.log_message.emit(f"账号 {phone} 未连接，跳过")

    async def _retrieve_groups(self, client, phone):
        try:
            groups = await self.get_group_info(client)
            self.log_message.emit(f"从账号 {phone} 获取到 {len(groups)} 个群组")
            self.group_info_retrieved.emit(groups)
        except Exception as e:
            self.log_message.emit(f"获取账号 {phone} 的群组信息时出错: {str(e)}")

    def start_monitoring(self, selected_groups):
        self.monitored_groups = set(selected_groups)
        for phone, worker in self.account_controller.workers.items():
            if worker.client and worker.client.is_connected():
                try:
                    worker.client.add_event_handler(self.on_new_message, events.NewMessage(chats=self.monitored_groups))
                    self.log_message.emit(f"账号 {phone} 开始监听 {len(self.monitored_groups)} 个群组")
                except Exception as e:
                    self.log_message.emit(f"账号 {phone} 开始监听时出错: {str(e)}")
        self.log_message.emit(f"共开始监听 {len(self.monitored_groups)} 个群组")

    def stop_monitoring(self):
        for phone, worker in self.account_controller.workers.items():
            if worker.client and worker.client.is_connected():
                try:
                    worker.client.remove_event_handler(self.on_new_message)
                    self.log_message.emit(f"账号 {phone} 停止监听")
                except Exception as e:
                    self.log_message.emit(f"账号 {phone} 停止监听时出错: {str(e)}")
        self.monitored_groups.clear()
        self.log_message.emit("停止所有群组监听")

    async def on_new_message(self, event):
        if event.chat_id in self.monitored_groups:
            sender = await event.get_sender()
            if isinstance(sender, User):
                last_online = self.get_last_online(sender.status)
                user_info = {
                    'username': sender.username,
                    'name': f"{sender.first_name} {sender.last_name}".strip(),
                    'chat_id': sender.id,
                    'last_online': last_online
                }
                self.user_activity_detected.emit(user_info)

    def get_last_online(self, status):
        if isinstance(status, UserStatusOnline):
            return "在线"
        elif isinstance(status, UserStatusOffline):
            return str(status.was_online)
        elif isinstance(status, UserStatusRecently):
            return "最近在线"
        elif isinstance(status, UserStatusLastWeek):
            return "上周在线"
        elif isinstance(status, UserStatusLastMonth):
            return "上月在线"
        else:
            return "未知状态"