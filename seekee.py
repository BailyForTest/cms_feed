# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


import json
import random
import hashlib
from queue import Queue

import requests
import threading
from datetime import datetime, timedelta


class FeedbackCount(threading.Thread):
    def __init__(self):
        super().__init__()
        self.login_url = "http://admin-push-api.otv.cc/quan/backend/auth/login"
        self.suggest_page = 'http://admin-push-api.otv.cc/quan/backend/suggest/page'
        self.token = self.login_cms()

    @staticmethod
    def is_first_letter_uppercase(s):
        for i, char in enumerate(s):
            if char.isupper():
                return True
        return False

    """ 第一步：登录cms，获取token"""
    def login_cms(self):
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/126.0.0.0 Safari/537.36'}
        data = {"userName": "baojie", "password": "Seekee@2024"}
        resp = requests.post(url=self.login_url, json=data, headers=header).json()
        return resp['data']

    """ 第二步：进入交互管理 - 反馈管理获取反馈信息"""
    def get_feedback(self, status, startDate, endDate):
        """
        :param status: 状态 待处理 0 已处理 1 已忽略 2
        :param endDate:   查询结束时间
        :param startDate: 开始时间时间
        :return:
        """
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'token': self.token,
                  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/126.0.0.0 Safari/537.36'}
        params = {
                "userId": "",
                "platformId": "",
                "clientType": "",
                "versionCode": "",
                "start": startDate,
                "end": endDate,
                "status": status,
                "page": 0,
                "size": 200
                }
        resp = requests.get(url=self.suggest_page, params=params, headers=header).json()
        return resp.get('data')

    """ 第三步：处理获取到的消息"""
    def send_message(self, hours):
        start_time = (datetime.now() + timedelta(hours=-hours)).strftime('%Y-%m-%d %H:%M:%S')
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        all_fq = self.get_feedback(0, start_time, end_time)
        url = "https://open.feishu.cn/open-apis/bot/v2/hook/9584496e-694a-41fd-a1bd-f8f8baff7168"
        # url = "https://open.feishu.cn/open-apis/bot/v2/hook/f6b2fd6a-5bd1-4fea-be82-5ef644e7fe5e"
        title = "近{}小时，后台有{}条未处理FQ".format(hours, all_fq.get('totalElements'))

        if all_fq.get('totalElements') == 0:
            data = "值得鼓励，再接再厉！！"
            self.webhook(url, title, data)
        else:
            # 处理列表
            processed_list = []
            for item in all_fq.get('content'):
                # 创建一个新字典，排除 'id' 字段
                new_item = {key: value for key, value in item.items() if key != 'id'}
                # 将 'time' 字段从毫秒级时间戳转换为可读的日期时间格式
                new_item['time'] = datetime.fromtimestamp(new_item['time'] / 1000).strftime(
                    '%Y-%m-%d %H:%M:%S')
                # 将content翻译为中文
                if new_item['content'] is None:
                    new_item['content'] = new_item['content']
                else:
                    new_item['content'] = str(self.translate_test(new_item['content']).get('trans_result')[0])
                processed_list.append(new_item)
            print()
            result = ["".join("{}: {}\n".format(k, v) for k, v in item.items()) for item in processed_list]
            result_string = "\n".join(result)
            data = result_string
            self.webhook(url, title, data)


    """ 消息分发 """
    @staticmethod
    def webhook(url, title,  data):
        header = {'Content-Type': 'application/json'}

        # 构建卡片消息的JSON对象
        card = {
                    "msg_type": "interactive",
                    "card": {
                        "elements": [{
                                "tag": "div",
                                "text": {
                                        "content": data,
                                        "tag": "lark_md"
                                }
                        },
                        ],
                        "header": {
                                "title": {
                                        "content": title,
                                        "tag": "plain_text"
                                }
                        }
                    }
                }
        response = requests.post(
            url,
            headers=header,
            data=json.dumps(card)
        )
        # 检查响应
        if response.status_code == 200:
            print("卡片消息发送成功")
        else:
            print("卡片消息发送失败", response.text)

    @staticmethod
    def translate_test(query):
        # Set your own appid/appkey.
        appid = '20241012002173630'
        appkey = 'ytbhHKyZOv8iltKUaK4R'

        # For list of language codes, please refer to `https://api.fanyi.baidu.com/doc/21`
        from_lang = 'auto'
        to_lang = 'zh'

        endpoint = 'http://api.fanyi.baidu.com'
        path = '/api/trans/vip/translate'
        url = endpoint + path

        # Generate salt and sign
        # def make_md5(s, encoding='utf-8'):
        #     return md5(s.encode(encoding)).hexdigest()

        salt = random.randint(32768, 65536)
        md5_hash = hashlib.md5()
        md5_hash.update((appid + query + str(salt) + appkey).encode())
        sign = md5_hash.hexdigest()
        # sign = make_md5(appid + query + str(salt) + appkey)

        # Build request
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {'appid': appid, 'q': query, 'from': from_lang, 'to': to_lang, 'salt': salt, 'sign': sign}

        # Send request
        r = requests.post(url, params=payload, headers=headers)
        result = r.json()

        # Show response
        # print(json.dumps(result, indent=4, ensure_ascii=False))
        return result


if __name__ == '__main__':
    count = FeedbackCount()
    # start_time = (datetime.now() + timedelta(hours=-1)).strftime('%Y-%m-%d %H:%M:%S')
    # end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    count.send_message(1)

