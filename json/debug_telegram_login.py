import asyncio
import json
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError


async def main():
    # 读取账号信息
    with open('14303101422.json', 'r') as f:
        credentials = json.load(f)

    phone = credentials['phone']
    api_id = credentials['app_id']
    api_hash = credentials['app_hash']
    session_file = credentials['session_file']

    print(f"正在尝试登录账号: {phone}")
    print(f"使用的 session 文件: {session_file}")

    client = TelegramClient(session_file, api_id, api_hash, system_version="4.16.30-vxCUSTOM")

    try:
        print("正在连接到 Telegram 服务器...")
        await client.connect()
        print("已连接到 Telegram 服务器")

        if not await client.is_user_authorized():
            print("Session 文件未授权，尝试登录...")
            try:
                await client.send_code_request(phone)
                print("验证码已发送，请查看您的 Telegram 应用")
                code = input("请输入收到的验证码: ")
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                print("需要两步验证密码")
                password = input("请输入您的两步验证密码: ")
                await client.sign_in(password=password)

        print("正在获取账号信息...")
        me = await client.get_me()
        print(f"成功登录为 {me.first_name} {me.last_name} (ID: {me.id})")

        print("正在获取对话列表...")
        async for dialog in client.iter_dialogs(limit=5):
            print(f"对话: {dialog.name} (ID: {dialog.id})")

    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        print("正在断开连接...")
        await client.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    asyncio.run(main())