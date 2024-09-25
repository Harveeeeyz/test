class Account:
    def __init__(self, phone, first_name, last_name, user_id, is_banned, phone_number):
        self.phone = phone
        self.first_name = first_name
        self.last_name = last_name
        self.user_id = user_id
        self.is_banned = is_banned
        self.phone_number = phone_number
        self.group_joined = False
        self.message_sent = False
        self.groups = set()  # 用于存储该账号加入的群组ID

    def add_group(self, group_id):
        self.groups.add(group_id)

    def remove_group(self, group_id):
        self.groups.discard(group_id)

    def __str__(self):
        return f"Account(phone={self.phone}, name={self.first_name} {self.last_name}, id={self.user_id})"