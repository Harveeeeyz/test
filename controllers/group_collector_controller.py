from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import Channel, Chat
import re
import logging
import asyncio

logger = logging.getLogger(__name__)

class GroupCollectorController:
    def __init__(self, account_controller):
        self.account_controller = account_controller
        self.collected_groups = {}  # 键为群组ID，值为包含账号信息的群组数据

    async def collect_groups(self, selected_accounts, keywords):
        bot_username = 'jisou123bot'
        for phone in selected_accounts:
            worker = self.account_controller.workers.get(phone)
            if worker and worker.client:
                client = worker.client
                yield f"开始处理账号 {phone}"
                logger.info(f"Processing account {phone}")
                try:
                    entity = await client.get_entity(bot_username)
                    yield f"成功连接到机器人: {bot_username}"

                    for keyword in keywords:
                        yield f"发送关键词: {keyword}"
                        try:
                            await client.send_message(entity, keyword)
                            async for message in client.iter_messages(entity, limit=5):
                                if message.sender_id == entity.id:
                                    yield "收到机器人回复，开始处理"
                                    all_links = set(re.findall(r'https://t\.me/[+\w]+', message.text))
                                    for link in all_links:
                                        try:
                                            link_entity = await client.get_entity(link)
                                            if isinstance(link_entity, (Chat, Channel)) and getattr(link_entity, 'megagroup', False):
                                                group_info = {
                                                    'name': link_entity.title,
                                                    'id': link_entity.id,
                                                    'link': link,
                                                    'members': getattr(link_entity, 'participants_count', None),
                                                    'account': phone  # 添加关联的账号
                                                }
                                                self.add_collected_group(group_info)
                                                yield group_info
                                        except FloodWaitError as e:
                                            yield f"处理链接 {link} 时遇到限制，需要等待 {e.seconds} 秒"
                                            await asyncio.sleep(e.seconds)
                                        except Exception as e:
                                            yield f"处理链接 {link} 时出错: {str(e)}"
                        except FloodWaitError as e:
                            yield f"发送关键词时遇到限制，需要等待 {e.seconds} 秒"
                            await asyncio.sleep(e.seconds)
                        except Exception as e:
                            yield f"发送关键词时出错: {str(e)}"

                except FloodWaitError as e:
                    yield f"账号 {phone} 遇到限制，需要等待 {e.seconds} 秒"
                    logger.warning(f"FloodWaitError for account {phone}: {str(e)}")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    yield f"处理账号 {phone} 时出错: {str(e)}"
                    logger.error(f"Error processing account {phone}: {str(e)}", exc_info=True)

    def get_collected_groups(self):
        return list(self.collected_groups.values())

    def add_collected_group(self, group_info):
        # 添加新收集到的群组，自动去重
        self.collected_groups[group_info['id']] = group_info

    async def get_joined_groups(self, account):
        client = self.account_controller.workers[account].client
        if not client:
            logger.error(f"No client found for account {account}")
            return []

        joined_groups = []
        async for dialog in client.iter_dialogs():
            if isinstance(dialog.entity, (Channel, Chat)) and dialog.is_group:
                group_info = {
                    'name': dialog.name,
                    'id': dialog.id,
                    'link': f"https://t.me/{dialog.entity.username}" if hasattr(dialog.entity, 'username') and dialog.entity.username else "无链接",
                    'account': account  # 添加账号信息
                }
                joined_groups.append(group_info)
        
        return joined_groups

    async def join_groups(self, account, group_links):
        client = self.account_controller.workers[account].client
        if not client:
            logger.error(f"No client found for account {account}")
            return

        for link in group_links:
            try:
                await client(JoinChannelRequest(link))
                logger.info(f"Successfully joined group: {link}")
            except Exception as e:
                logger.error(f"Failed to join group {link}: {str(e)}")