import asyncio
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.types import MessageService
import logging
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载配置
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# API凭证和其他配置
API_ID = config['api_id']
API_HASH = config['api_hash']
BOT_TOKEN = config['bot_token']
USER_PHONE = config['user_phone']
TWO_FA_PASSWORD = config.get('two_fa_password', '')
SOURCE_GROUP_ID = config['source_group_id']
TARGET_GROUP_ID = config['target_group_id']

# 初始化客户端
user_client = TelegramClient('user_session', API_ID, API_HASH)
bot_client = TelegramClient('bot_session', API_ID, API_HASH)

# 存储消息和定时任务
messages = []
scheduled_tasks = {}
user_state = {}


async def user_client_login():
    try:
        await user_client.start()
        if not await user_client.is_user_authorized():
            await user_client.send_code_request(USER_PHONE)
            code = input('请输入您收到的验证码: ')
            await user_client.sign_in(USER_PHONE, code)
            if TWO_FA_PASSWORD:
                await user_client.sign_in(password=TWO_FA_PASSWORD)
        logger.info("用户客户端已成功登录")
    except PhoneCodeInvalidError:
        logger.error("验证码无效")
    except SessionPasswordNeededError:
        logger.error("需要二步验证密码")
    except Exception as e:
        logger.error(f"登录过程中发生错误: {e}")
        raise


@bot_client.on(events.NewMessage(pattern='/start'))
async def start(event):
    keyboard = [
        [Button.text("/list"), Button.text("/forward"), Button.text("/schedule")],
        [Button.text("/stop"), Button.text("/queue"), Button.text("/help")]
    ]
    await event.reply("欢迎使用转发Bot！请选择一个命令：", buttons=keyboard)


@bot_client.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    help_text = """
使用说明：

/list - 列出源群组的最新10条消息
/forward - 转发指定消息
/schedule - 设置定时转发
/stop - 停止定时转发任务
/queue - 显示当前定时转发任务队列
/help - 显示此帮助信息

详细使用方法请参考各命令的提示。
    """
    await event.reply(help_text)


@bot_client.on(events.NewMessage(pattern='/list'))
async def list_messages(event):
    global messages
    messages = []
    msg = "源群组最新消息：\n"
    async for message in user_client.iter_messages(SOURCE_GROUP_ID, limit=10):
        messages.append(message)

    for i, message in enumerate(messages, 1):
        content = message.text if message.text else "（媒体文件或其他类型消息）"
        msg += f"{i}. {content[:20]}{'...' if len(content) > 20 else ''}\n"

    await event.reply(msg)


@bot_client.on(events.NewMessage(pattern='/forward'))
async def forward_message_prompt(event):
    user_state[event.sender_id] = 'awaiting_forward_numbers'
    await event.reply("请输入要转发的消息编号，多个编号用空格分隔（例如：1 3 5）")


@bot_client.on(events.NewMessage(pattern='/schedule'))
async def schedule_prompt(event):
    user_state[event.sender_id] = 'awaiting_schedule_numbers'
    await event.reply("请输入要定时转发的消息编号和时间间隔（秒），格式：消息编号 间隔\n例如：1 3 5 3600（表示每小时转发1、3、5号消息）")


@bot_client.on(events.NewMessage(
    func=lambda e: user_state.get(e.sender_id) in ['awaiting_forward_numbers', 'awaiting_schedule_numbers']))
async def process_numbers(event):
    user_id = event.sender_id
    state = user_state.get(user_id)

    if state == 'awaiting_forward_numbers':
        message_numbers = [int(num) for num in event.text.split() if num.isdigit()]
        await forward_messages(event, message_numbers)
    elif state == 'awaiting_schedule_numbers':
        parts = event.text.split()
        if len(parts) < 2 or not parts[-1].isdigit():
            await event.reply("格式错误，请按照 '消息编号 间隔' 的格式输入")
            return
        message_numbers = [int(num) for num in parts[:-1] if num.isdigit()]
        interval = int(parts[-1])
        await set_schedule(event, message_numbers, interval)

    del user_state[user_id]


async def forward_messages(event, message_numbers):
    if not message_numbers:
        await event.reply("请输入有效的消息编号")
        return

    invalid_numbers = [num for num in message_numbers if num < 1 or num > len(messages)]

    if invalid_numbers:
        await event.reply(f"无效的消息编号: {', '.join(map(str, invalid_numbers))}")
        return

    try:
        for num in message_numbers:
            message_to_forward = messages[num - 1]
            if not isinstance(message_to_forward, MessageService):
                await user_client.send_message(TARGET_GROUP_ID, message_to_forward)

        await event.reply(f"已成功转发以下消息: {', '.join(map(str, message_numbers))}")
    except Exception as e:
        logger.error(f"转发消息时发生错误: {e}")
        await event.reply(f"转发消息时发生错误: {str(e)}")


async def schedule_forward(message_numbers, interval):
    while True:
        try:
            for num in message_numbers:
                message_to_forward = messages[num - 1]
                if not isinstance(message_to_forward, MessageService):
                    await user_client.send_message(TARGET_GROUP_ID, message_to_forward)
            logger.info(f"定时转发完成: {', '.join(map(str, message_numbers))}")
        except Exception as e:
            logger.error(f"定时转发时发生错误: {e}")

        await asyncio.sleep(interval)


async def set_schedule(event, message_numbers, interval):
    if not message_numbers:
        await event.reply("请输入有效的消息编号")
        return

    invalid_numbers = [num for num in message_numbers if num < 1 or num > len(messages)]

    if invalid_numbers:
        await event.reply(f"无效的消息编号: {', '.join(map(str, invalid_numbers))}")
        return

    task = asyncio.create_task(schedule_forward(message_numbers, interval))
    task_id = f"{event.chat_id}_{event.id}"
    scheduled_tasks[task_id] = (task, message_numbers, interval)

    await event.reply(f"已设置定时转发任务，每 {interval} 秒转发一次以下消息: {', '.join(map(str, message_numbers))}")


@bot_client.on(events.NewMessage(pattern='/stop'))
async def stop_tasks(event):
    if not scheduled_tasks:
        await event.reply("当前没有正在运行的定时任务")
        return

    msg = "当前定时任务：\n"
    for i, (task_id, (_, message_numbers, interval)) in enumerate(scheduled_tasks.items(), 1):
        msg += f"{i}. 任务ID: {task_id}, 消息: {', '.join(map(str, message_numbers))}, 间隔: {interval}秒\n"

    msg += "\n请输入要停止的任务编号，多个编号用空格分隔（例如：1 3），或输入 'all' 停止所有任务"
    await event.reply(msg)

    user_state[event.sender_id] = 'awaiting_stop_numbers'


@bot_client.on(events.NewMessage(func=lambda e: user_state.get(e.sender_id) == 'awaiting_stop_numbers'))
async def stop_selected_tasks(event):
    user_id = event.sender_id
    if event.text.lower() == 'all':
        for task, _, _ in scheduled_tasks.values():
            task.cancel()
        scheduled_tasks.clear()
        await event.reply("所有定时任务已停止")
    else:
        task_numbers = [int(num) for num in event.text.split() if num.isdigit()]
        tasks_to_stop = list(scheduled_tasks.items())
        stopped_tasks = []
        for num in task_numbers:
            if 1 <= num <= len(tasks_to_stop):
                task_id, (task, _, _) = tasks_to_stop[num - 1]
                task.cancel()
                del scheduled_tasks[task_id]
                stopped_tasks.append(str(num))
        if stopped_tasks:
            await event.reply(f"已停止以下任务: {', '.join(stopped_tasks)}")
        else:
            await event.reply("没有停止任何任务，请确保输入了正确的任务编号")

    del user_state[user_id]


@bot_client.on(events.NewMessage(pattern='/queue'))
async def show_queue(event):
    if not scheduled_tasks:
        await event.reply("当前没有正在运行的定时任务")
        return

    msg = "当前定时任务队列：\n"
    for task_id, (_, message_numbers, interval) in scheduled_tasks.items():
        msg += f"任务ID: {task_id}\n"
        msg += f"转发消息: {', '.join(map(str, message_numbers))}\n"
        msg += f"间隔: {interval} 秒\n"
        for num in message_numbers:
            content = messages[num - 1].text if messages[num - 1].text else "（媒体文件或其他类型消息）"
            msg += f"  {num}. {content[:20]}{'...' if len(content) > 20 else ''}\n"
        msg += "\n"

    await event.reply(msg)


async def main():
    try:
        await user_client_login()
        await bot_client.start(bot_token=BOT_TOKEN)
        logger.info("Bot客户端已启动")

        await bot_client.run_until_disconnected()
    except Exception as e:
        logger.error(f"运行过程中发生错误: {e}")
    finally:
        for task, _, _ in scheduled_tasks.values():
            task.cancel()
        await user_client.disconnect()
        await bot_client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
