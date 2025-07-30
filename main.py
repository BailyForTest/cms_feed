#!/usr/local/bin/python
# -*- coding: UTF-8 -*-
# @Project : loklok
# @Time    : 2024/7/26 17:15
# @Author  : bj
# @Email   : 475829130@qq.com
# @File    : feedback_count.py
# @Software: PyCharm
import hashlib
import json
import random
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import requests


class FeedbackCount(threading.Thread):
    FEEDBACK_TYPES = {
        25: '产品相关', 26: '关于loklok tv', 27: '关于PC', 29: 'VIP相关',
        30: '内容/字幕相关问题', 31: '账号问题', 32: '未成年模式', 33: '一起看',
        34: '联系我', 35: '功能引导', 36: '其他', 37: '其他'
    }

    WEBHOOK_URLS = {
        'Android': 'https://open.feishu.cn/open-apis/bot/v2/hook/cdc47192-c4dd-4b38-b530-bd6063a60c48',
        # 'Android': 'https://open.feishu.cn/open-apis/bot/v2/hook/f6b2fd6a-5bd1-4fea-be82-5ef644e7fe5e',
        'iOS': 'https://open.feishu.cn/open-apis/bot/v2/hook/3b0f5a23-d5cd-45a4-9f53-033f1d62a351'
        # 'iOS': 'https://open.feishu.cn/open-apis/bot/v2/hook/f6b2fd6a-5bd1-4fea-be82-5ef644e7fe5e'
    }

    CMS_LOGIN_URL = "https://admin-api.netpop.app/auth/backend/account/login"
    FEEDBACK_URL = 'https://admin-api.netpop.app/user/behavior/backend/feedback/v2/page/0'
    TRANSLATE_URL = "https://admin-api.netpop.app/third/backend/openai/translate"

    HEADERS = {
        'Content-Type': 'application/json;charset=UTF-8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }

    def __init__(self):
        super().__init__()
        self.token = self.login_cms()
        self.now = datetime.now()
        self.results = []

    @staticmethod
    def get_time_range(hours=0, days=0):
        """获取时间范围"""
        start = datetime.now() - timedelta(hours=hours, days=days)
        return (
            start.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S'),
            datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        )

    def login_cms(self):
        """登录CMS获取token"""
        data = {"username": "testrobot", "password": "Testrobot9456@"}
        resp = requests.post(self.CMS_LOGIN_URL, json=data, headers=self.HEADERS).json()
        return resp.get('data', '')

    def get_feedback(self, feedback_type, start_date, end_date, page=0, size=200):
        """获取反馈数据"""
        headers = {**self.HEADERS, 'token': self.token}
        data = {
            "types": feedback_type, "startDate": start_date, "endDate": end_date,
            "page": page, "size": size
        }
        resp = requests.post(self.FEEDBACK_URL, json=data, headers=headers).json()
        return resp.get('data', {})

    def get_feedback_detail(self, feedback_id):
        """获取反馈详情"""
        url = f'https://admin-api.netpop.app/user/behavior/backend/feedback/v2/detail/{feedback_id}'
        headers = {**self.HEADERS, 'token': self.token}
        resp = requests.get(url, headers=headers).json()
        return resp.get('data', {})

    def translate_text(self, text):
        """翻译文本"""
        headers = {
            **self.HEADERS,
            "token": self.token,
            "Content-Type": "text/plain"
        }
        params = {"lan": "中文"}
        response = requests.post(self.TRANSLATE_URL, data=text.encode('utf-8'),
                                 headers=headers, params=params)
        return response.json().get("data", "")

    def process_feedback(self, feedback_type, start_time, end_time):
        """处理单个反馈类型的数据"""
        type_name = self.FEEDBACK_TYPES[feedback_type]
        data = self.get_feedback([feedback_type], start_time, end_time)

        if not data or not data.get('content'):
            return {type_name: []}

        processed = []
        for item in data['content']:
            detail = self.get_feedback_detail(item['id'])
            text_data = {
                "用户ID": str(item.get('userId', 'None')),
                "IP地区": item.get('region', detail.get('region', '')),
                "IP地址": item.get('ipAddress', detail.get('ipAddress', '')),
                "版本渠道": item.get('appName', ''),
                "问题描述": self.format_description(item.get('question', '')),
                "设备ID": item.get('deviceId', ''),
                "版本信息": item.get('appVersion', ''),
                "反馈时间": item.get('createTime', ''),
                "反馈截图": self.format_images(detail.get('imgUrl', ''))
            }
            processed.append(text_data)
        return {type_name: processed}

    def format_description(self, text):
        """格式化问题描述（添加翻译）"""
        if not text:
            return ""
        translated = self.translate_text(text)
        return f"\n原文：{text}\n译文：{translated}"

    @staticmethod
    def format_images(img_url):
        """格式化图片URL"""
        if not img_url:
            return ""
        return img_url.strip('[]').replace('"', "").replace(',', "\\n")

    def send_to_feishu(self, data, platform):
        """发送数据到飞书"""
        if not data:
            return

        url = self.WEBHOOK_URLS.get(platform)
        if not url:
            return

        card = {
            "msg_type": "interactive",
            "card": {
                "elements": [{
                    "tag": "div",
                    "text": {"content": data, "tag": "lark_md"}
                }],
                "header": {"title": {"content": "用户反馈", "tag": "plain_text"}}
            }
        }
        requests.post(url, json=card)

    def get_recent_feedback(self, hours=2):
        """获取最近几小时的反馈"""
        start_time = (self.now - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        end_time = self.now.strftime('%Y-%m-%d %H:%M:%S')

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.process_feedback, ft, start_time, end_time)
                       for ft in self.FEEDBACK_TYPES]
            self.results = [future.result() for future in futures]

        # 按平台分类发送
        ios_data, android_data = "", ""
        for result in self.results:
            for type_name, items in result.items():
                if not items:
                    continue

                type_header = f"{type_name}:\n"
                for item in items:
                    content = "\n".join(f"{k}: {v}" for k, v in item.items()) + "\n\n"
                    if item['设备ID'].isupper():
                        ios_data += type_header + content
                    else:
                        android_data += type_header + content
                    type_header = ""  # 只在第一个条目显示类型标题

        if ios_data:
            self.send_to_feishu(ios_data, 'iOS')
        if android_data:
            self.send_to_feishu(android_data, 'Android')

    def get_weekly_summary(self):
        """获取周汇总数据"""
        this_week = self.get_time_range(days=7)
        last_week = (self.now - timedelta(days=14), self.now - timedelta(days=8))

        this_week_data = self.get_feedback_count(this_week[0], this_week[1])
        last_week_data = self.get_feedback_count(last_week[0], last_week[1])

        summary = f"本周反馈总数: {this_week_data['total']}\n" \
                  f"上周反馈总数: {last_week_data['total']}\n\n" \
                  "本周分类统计:\n" + \
                  "\n".join(f"{k}: {v}" for k, v in this_week_data.items() if k != 'total')

        self.send_to_feishu(summary, 'Android')

    def get_feedback_count(self, start_date, end_date):
        """获取反馈统计"""
        counts = {'total': 0}
        for ft, name in self.FEEDBACK_TYPES.items():
            data = self.get_feedback([ft], start_date, end_date)
            count = data.get('totalElements', 0)
            counts[name] = count
            counts['total'] += count
        return counts

    def run(self):
        """主运行逻辑"""
        if datetime.now().weekday() == 3 and datetime.now().hour == 15:  # 周四下午3点
            self.get_weekly_summary()

        current_hour = datetime.now().hour
        if 8 < current_hour <= 23:  # 9-23点每小时运行
            self.get_recent_feedback(hours=1)
        elif current_hour == 8:  # 早上8点
            self.get_recent_feedback(hours=8)


if __name__ == '__main__':
    count = FeedbackCount()
    count.run()
