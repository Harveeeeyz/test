import logging
import asyncio
from PyQt6.QtCore import QObject, pyqtSignal
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.errors import SessionPasswordNeededError
from telethon import functions

logger = logging.getLogger(__name__)

class TelegramWorker(QObject):
    log_message = pyqtSignal(str)
    login_success = pyqtSignal(str, str, str, str, bool, str)  # phone, first_name, last_name, user_id, is_banned, phone_number
    profile_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    client_ready = pyqtSignal()

    def __init__(self, phone, api_id, api_hash, two_fa_password, loop, session_path):
        super().__init__()
        self.phone = phone
        self.api_id = api_id
        self.api_hash = api_hash
        self.two_fa_password = two_fa_password
        self.loop = loop
        self.session_path = session_path
        self.client = None
        self.is_running = False

    async def run(self):
        self.is_running = True
        try:
            await self.main()
        except Exception as e:
            self.error_occurred.emit(f"Error in worker: {str(e)}")
            logger.error(f"Error in worker for {self.phone}: {str(e)}", exc_info=True)
        finally:
            self.is_running = False

    async def main(self):
        try:
            self.client = TelegramClient(self.session_path, self.api_id, self.api_hash, loop=self.loop)
            await self.client.connect()
            
            if await self.client.is_user_authorized():
                await self.get_and_emit_account_info()
            else:
                self.client_ready.emit()
        except Exception as e:
            logger.error(f"Error starting client for {self.phone}: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"Error starting client: {str(e)}")
        
        while self.is_running:
            await asyncio.sleep(1)

    def stop(self):
        self.is_running = False
        if self.client:
            asyncio.create_task(self.client.disconnect())

    async def send_code(self):
        if not self.client:
            self.error_occurred.emit("Client not initialized")
            return
        
        try:
            await self.client.send_code_request(self.phone)
            self.log_message.emit(f"验证码已发送到 {self.phone}")
        except Exception as e:
            self.error_occurred.emit(f"发送验证码失败: {str(e)}")

    async def login(self, code):
        if not self.client:
            self.error_occurred.emit("Client not initialized")
            return

        try:
            await self.client.sign_in(self.phone, code)
        except SessionPasswordNeededError:
            if self.two_fa_password:
                await self.client.sign_in(password=self.two_fa_password)
            else:
                self.error_occurred.emit("Two-factor authentication is required, but no password was provided")
                return
        except Exception as e:
            self.error_occurred.emit(f"登录失败: {str(e)}")
            return

        await self.get_and_emit_account_info()

    async def get_and_emit_account_info(self):
        try:
            me = await self.client.get_me()
            full_user = await self.client(functions.users.GetFullUserRequest(me.id))
            is_banned = False  # Telethon 不直接提供此信息，可能需要其他方式判断
            phone_number = me.phone
            self.login_success.emit(self.phone, me.first_name, me.last_name, str(me.id), is_banned, phone_number)
            logger.info(f"Emitting login success for {self.phone}")  # 确保这里的缩进是 4 个空格
        except Exception as e:
            self.error_occurred.emit(f"获取账号信息失败: {str(e)}")
            logger.error(f"Error getting account info: {str(e)}", exc_info=True)

    async def update_profile(self, first_name=None, last_name=None, about=None, photo_path=None):
        if not self.client:
            self.error_occurred.emit("Client not initialized")
            return

        try:
            if first_name or last_name or about:
                await self.client(UpdateProfileRequest(
                    first_name=first_name,
                    last_name=last_name,
                    about=about
                ))
            if photo_path:
                await self.client(UploadProfilePhotoRequest(
                    await self.client.upload_file(photo_path)
                ))
            self.profile_updated.emit(self.phone)
            self.log_message.emit(f"账号 {self.phone} 的资料已更新")
        except Exception as e:
            self.error_occurred.emit(f"更新资料失败: {str(e)}")
