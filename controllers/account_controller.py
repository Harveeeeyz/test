import logging
import asyncio
from models.account import Account
from workers.telegram_worker import TelegramWorker
from PyQt6.QtCore import QObject, pyqtSignal
import json
import os

logger = logging.getLogger(__name__)


class AccountController(QObject):
    account_logged_in = pyqtSignal(str, str, str, str, bool,
                                   str)  # phone, first_name, last_name, user_id, is_banned, phone_number

    def __init__(self, loop):
        super().__init__()
        self.accounts = {}
        self.workers = {}
        self.api_credentials = self.load_api_credentials()
        self.loop = loop
        self.json_dir = 'json'
        if not os.path.exists(self.json_dir):
            os.makedirs(self.json_dir)

    def create_worker(self, phone, api_id, api_hash, two_fa_password):
        session_path = os.path.join(self.json_dir, f"{phone}.session")
        worker = TelegramWorker(phone, api_id, api_hash, two_fa_password, self.loop, session_path)
        self.workers[phone] = worker
        return worker

    def get_api_credentials(self, phone):
        return self.api_credentials.get(phone)

    def save_api_credentials(self, phone, api_id, api_hash):
        self.api_credentials[phone] = {'app_id': api_id, 'app_hash': api_hash}
        self._save_api_credentials_to_file()

    def load_api_credentials(self):
        try:
            with open('api_credentials.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _save_api_credentials_to_file(self):
        with open('api_credentials.json', 'w') as f:
            json.dump(self.api_credentials, f)

    async def start_worker(self, phone):
        if phone in self.workers:
            await self.workers[phone].run()

    async def send_code(self, phone):
        if phone in self.workers:
            await self.workers[phone].send_code()

    async def login(self, phone, code, two_fa_password):
        if phone in self.workers:
            self.workers[phone].two_fa_password = two_fa_password
            await self.workers[phone].login(code)

    def add_account(self, phone, first_name, last_name, user_id, is_banned, phone_number):
        account = Account(phone, first_name, last_name, user_id, is_banned, phone_number)
        self.accounts[phone] = account

    async def update_profile(self, phone, first_name=None, last_name=None, about=None, photo_path=None):
        if phone in self.workers:
            await self.workers[phone].update_profile(first_name, last_name, about, photo_path)

    def get_all_accounts(self):
        return list(self.accounts.values())

    def stop_all_workers(self):
        for worker in self.workers.values():
            worker.stop()

    def get_account(self, phone):
        return self.accounts.get(phone)

    async def session_login(self, session_file=None):
        if session_file:
            return await self._login_single_session(session_file)
        else:
            return await self._login_all_sessions()

    async def _login_single_session(self, session_file):
        phone = os.path.basename(session_file).split('.')[0]
        json_file = os.path.join(self.json_dir, f"{phone}.json")

        if not os.path.exists(json_file):
            logger.error(f"JSON file not found for {phone}")
            return f"JSON file not found for {phone}"

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            api_id = data['app_id']
            api_hash = data['app_hash']
            two_fa_password = data.get('twoFA', '')

            worker = self.create_worker(phone, api_id, api_hash, two_fa_password)
            worker.login_success.connect(self.on_login_success)
            worker.error_occurred.connect(self.on_login_error)
            await self.start_worker(phone)
            logger.info(f"Started login process for {phone}")
            return f"Started login process for {phone}"
        except Exception as e:
            logger.error(f"Error during login process for {phone}: {str(e)}", exc_info=True)
            return f"Error during login process for {phone}: {str(e)}"

    async def _login_all_sessions(self):
        login_results = []
        tasks = []
        for filename in os.listdir(self.json_dir):
            if filename.endswith('.json'):
                phone = filename.split('.')[0]
                session_file = os.path.join(self.json_dir, f"{phone}.session")
                if os.path.exists(session_file):
                    tasks.append(self._login_single_session(session_file))
                else:
                    login_results.append(f"Session file not found for {phone}")

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error during batch login: {str(result)}")
                    login_results.append(f"Error: {str(result)}")
                else:
                    login_results.append(result)

        return login_results

    async def batch_login(self):
        return await self._login_all_sessions()

    def on_login_success(self, phone, first_name, last_name, user_id, is_banned, phone_number):
        self.add_account(phone, first_name, last_name, user_id, is_banned, phone_number)
        logger.info(f"Successfully logged in: {phone}")
        self.account_logged_in.emit(phone, first_name, last_name, user_id, is_banned, phone_number)

    def on_login_error(self, error_message):
        logger.error(f"Login error: {error_message}")