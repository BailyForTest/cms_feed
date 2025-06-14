#!/usr/local/bin/python
# -*- coding:UTF-8 -*-
# @Project : loklok
# @Time    : 2024/7/26 17:15
# @Author  : bj
# @Email   : 475829130@qq.com
# @File    : feedback_count.py
# @Software: PyCharm
import hashlib
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
        self.login_url = "https://admin-api.netpop.app/auth/backend/account/login"
        self.get_feedback_url = 'https://admin-api.netpop.app/user/behavior/backend/feedback/v2/page/0'
        self.token = self.login_cms()
        self.feedback_type_list = {25: '产品相关',
                                   26: '关于loklok tv',
                                   27: '关于PC',
                                   # 28: 'VIP相关',
                                   29: 'VIP相关',
                                   30: '内容/字幕相关问题',
                                   31: '账号问题',
                                   32: '未成年模式',
                                   33: '一起看',
                                   34: '联系我',
                                   35: '功能引导',
                                   36: '其他',
                                   37: '其他'
                                  }
        self.results = []

        self.now_time = datetime.now()
        self.today_time = self.start_or_end(self.now_time)
        self.yesterday_time = self.start_or_end(self.now_time + timedelta(days=-1))
        """ self.this_week[] - self.yesterday_time[1] """
        self.this_week = [self.start_or_end(self.now_time + timedelta(days=-7))[0],
                          self.yesterday_time[1]]
        """ 上周的数据 """
        self.last_week = [self.start_or_end(self.now_time + timedelta(days=-14))[0],
                          self.start_or_end(self.now_time + timedelta(days=-8))[1]]

        """ 本月的数据 """
        self.this_month = [self.start_or_end(self.now_time + timedelta(days=-31))[0],
                           self.yesterday_time[1]]
        """ 本月的数据 """
        self.last_month = [self.start_or_end(self.now_time + timedelta(days=-62))[0],
                           self.start_or_end(self.now_time + timedelta(days=-32))[1]]

    @staticmethod
    def start_or_end(date):
        startDate = date.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        endDate = date.replace(hour=23, minute=59, second=59, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        return startDate, endDate

    @staticmethod
    def is_first_letter_uppercase(s):
        for i, char in enumerate(s):
            if char.isupper():
                return True
        return False

    """ 登录cms，获取token"""
    def login_cms(self):
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/126.0.0.0 Safari/537.36'}
        data = {"username": "testrobot", "password": "Testrobot9456@"}
        resp = requests.post(url=self.login_url, json=data, headers=header).json()
        return resp['data']

    def get_feedback(self, feedback_type, startDate, endDate):
        """
        :param endDate:
        :param startDate:
        :param feedback_type:
        :return:
        """
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'token': self.token,
                  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/126.0.0.0 Safari/537.36'}
        data = {"id": "",
                "contactWay": "",
                "userId": "",
                "types": feedback_type,
                "status": "",
                "dataRange": [],
                "startDate": startDate,
                "endDate": endDate,
                "page": 0,
                "size": 200}
        resp = requests.post(url=self.get_feedback_url, json=data, headers=header).json()
        return resp.get('data')

    def feedback_details(self, feedback_id):
        url = 'https://admin-api.netpop.app/user/behavior/backend/feedback/v2/detail/{}'.format(feedback_id)
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'token': self.token,
                  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/126.0.0.0 Safari/537.36'}
        resp = requests.get(url=url, headers=header).json()
        return resp.get('data')

    @staticmethod
    def __assert(result_queue, type_name, data):
        all_feed, feed_info, text_data = [], {}, ''
        feed_info[type_name] = []
        if not data:
            text_data = '{}近段时间无反馈:'.format(type_name)
        else:
            for eve_data in data.get('content'):
                """ statusDesc:状态  appVersion  deviceId   region"""
                # print(eve_data)
                text_data = {}
                if eve_data.get('userId'):
                    text_data["用户ID: "] = str(eve_data.get('userId'))
                else:
                    text_data["用户ID: "] = 'None'
                if eve_data.get('region'):
                    text_data["IP地区: "] = eve_data.get('region')
                if eve_data.get('ipAddress'):
                    text_data["IP地址: "] = eve_data.get('ipAddress')
                if eve_data.get('appName'):
                    text_data["版本渠道: "] = eve_data.get('appName')
                if eve_data.get('question'):
                    text_data["问题描述: "] = eve_data.get('question')
                if eve_data.get('deviceId'):
                    text_data["设备ID: "] = eve_data.get('deviceId')
                if eve_data.get('appVersion'):
                    text_data["版本信息: "] = eve_data.get('appVersion')
                if eve_data.get('createTime'):
                    text_data["反馈时间: "] = eve_data.get('createTime')
                if count.feedback_details(eve_data.get('id')).get('imgUrl'):
                    imgUrl = count.feedback_details(eve_data.get('id')).get('imgUrl')
                    imgUrl = imgUrl.strip('[]')
                    imgUrl = imgUrl.replace('"', "")
                    imgUrl = imgUrl.replace(',', "\\n")
                    text_data["反馈截图: "] = imgUrl
                feed_info[type_name].append(text_data)
            result_queue.put(feed_info)

    def count_feed(self, feedback_type_list, start_Time, end_Time, des='hours'):
        count_data = {des: {"all_count": 0}}
        for type_key in feedback_type_list.keys():
            now_data = self.get_feedback([type_key], start_Time, end_Time)
            count_data[des]['all_count'] += now_data.get('totalElements')
            type_name = feedback_type_list[type_key]
            count_data[des][type_name] = now_data.get('totalElements')
            # input_text += self.__assert(des, type_name, now_data.get('content')) + '\n'
        print('{}合计反馈数：{}'.format(des, count_data))
        return count_data

    def get_hours_feed_info(self, hours=2):
        """ 最近X小时的反馈内容 """
        start_time = (self.now_time + timedelta(hours=-hours)).strftime('%Y-%m-%d %H:%M:%S')
        end_time = self.now_time.strftime('%Y-%m-%d %H:%M:%S')
        result_queue = Queue()
        threads = []
        for type_key in self.feedback_type_list.keys():
            type_name = self.feedback_type_list[type_key]
            now_data = self.get_feedback([type_key],
                                         start_time,
                                         end_time)
            # self.__assert(des, type_name, now_data.get('content'))
            thread = threading.Thread(target=FeedbackCount.__assert,
                                      name=type_name,
                                      args=(result_queue, type_name, now_data, ))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        while not result_queue.empty():
            self.results.append(result_queue.get())

        """ 转化为飞书消息格式 """
        all_data = {}
        for type_data in self.results:
            for k, v in type_data.items():
                txt = "{}:".format(str(k)) + "\n"
                # print('-----------------------------------v:{}-----------------------------------------'.format(v))
                IOS, Android = '', ''
                if len(v) != 0:
                    for v1 in v:
                        print( v1['问题描述: '])
                        # v1['问题描述: '] = self.translate_test(v1['问题描述: '])["trans_result"]
                        yuanwen = " \n"+"原文："+v1['问题描述: '] + " \n"
                        yiwen = "译文："+self.translate_test1(v1['问题描述: '])
                        v1['问题描述: '] = yuanwen + yiwen
                        str_v1 = ''
                        for key, value in v1.items():
                            str_v1 += str(key) + str(value) + " \n"
                        """ IOS用户 """
                        if self.is_first_letter_uppercase(v1['设备ID: ']) is True:
                            IOS += str_v1 + " \n"
                        else:
                            Android += str_v1 + " \n"
                        # if self.is_first_letter_uppercase(v1['设备ID: ']) is True:
                        #     v1['问题描述: '] = self.translate_test(v1['问题描述: '])["trans_result"]
                        #     IOS += str(v1) + "\n"
                        # else:
                        #     v1['问题描述: '] = self.translate_test(v1['问题描述: '])["trans_result"]
                        #     Android += str(v1) + "\n"

                    if IOS != '':
                        ios_data = {"msg_type": "text",
                                    "content":
                                        {"text": txt + IOS}}
                        self.webhook(url='https://open.feishu.cn/open-apis/bot/v2/hook/3b0f5a23-d5cd-45a4-9f53-033f1d62a351', title=txt, data=IOS)
                        # self.webhook(url='https://open.feishu.cn/open-apis/bot/v2/hook/f6b2fd6a-5bd1-4fea-be82-5ef644e7fe5e', title=txt, data=IOS)

                    if Android != '':
                        android_data = {"msg_type": "text",
                                        "content":
                                            {"text": txt + Android}}
                        self.webhook(url='https://open.feishu.cn/open-apis/bot/v2/hook/cdc47192-c4dd-4b38-b530-bd6063a60c48', title=txt, data=Android)
                        # self.webhook(url='https://open.feishu.cn/open-apis/bot/v2/hook/f6b2fd6a-5bd1-4fea-be82-5ef644e7fe5e', title=txt, data=Android)
                else:
                    txt = "------------------------------{}:{} to {}:----------------------------". \
                               format(str(k), start_time, end_time, ) + "\n" + "近期无反馈"
                    data = {"msg_type": "text",
                            "content":
                                {"text": txt}
                            }
                    print(data)
                    # self.webhook("", data)

    def get_all_feed(self, hours=2):
        """本周的反馈数据：截至到yesterday """
        print(self.this_week)
        this_week = count.count_feed(self.feedback_type_list,
                                     self.this_week[0], self.this_week[1], des="this_week")
        """上周的反馈数据 """
        print(self.last_week)
        last_week = count.count_feed(self.feedback_type_list,
                                     self.last_week[0], self.last_week[1], des="last_week")
        all_data = str(this_week) + "\n" + \
                   str(last_week) + "\n"

        data = {"msg_type": "text",
                "content":
                    {"text": all_data}
                }
        # self.webhook("https://open.feishu.cn/open-apis/bot/v2/hook/f6b2fd6a-5bd1-4fea-be82-5ef644e7fe5e", title="周报", data=all_data)
        self.webhook(url='https://open.feishu.cn/open-apis/bot/v2/hook/cdc47192-c4dd-4b38-b530-bd6063a60c48', title="一周总结", data=all_data)

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
                        },],
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
        print(json.dumps(result, indent=4, ensure_ascii=False))
        return result
        
    def translate_test1(self, payload):
        url = "https://admin-api.netpop.app/third/backend/openai/translate"

        querystring = {"lan": "中文"}
        payload = payload.encode('utf-8')  # 将字符串转为 UTF-8 字节
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "origin": "https://admin.netpop.app",
            "priority": "u=1, i",
            "referer": "https://admin.netpop.app/",
            "sec-ch-ua": f'"Google Chrome";v="131", "Chromium";v="131", "Not:A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Windows",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "token": self.token,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Content-Type": "text/plain",
            "content-type": "application/x-www-form-urlencoded"
        }
        response = requests.request("POST", url, data=payload, headers=headers, params=querystring)
        print(response.json())
        return response.json().get("data")


if __name__ == '__main__':
    count = FeedbackCount()

    """ 周一 - 周五"""
    if datetime.now().weekday() <= 6:
        if datetime.now().weekday() == 3 and datetime.now().hour == 15:
            count.get_all_feed()
        """ 每隔两个小时发送一次推送 """
        if 8 < datetime.now().hour <= 23:
            count.get_hours_feed_info(hours=1)
        """ 每天早上8点发送一次 """
        if datetime.now().hour == 8:
            count.get_hours_feed_info(hours=8)
        else:
            pass
    else:
        if (datetime.now().hour % 8) == 0:
            count.get_hours_feed_info(hours=8)
