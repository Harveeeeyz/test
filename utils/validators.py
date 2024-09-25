import re

def validate_phone_number(phone):
    """
    验证电话号码格式是否正确
    :param phone: 电话号码字符串
    :return: 如果格式正确返回True，否则返回False
    """
    pattern = r'^\+[1-9]\d{1,14}$'
    return re.match(pattern, phone) is not None