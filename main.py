#!/usr/local/bin/python
# -*- coding:UTF-8 -*-
# @Project : loklok
# @Time    : 2024/7/26 17:15
# @Author  : bj
# @Email   : 475829130@qq.com
# @File    : feedback_count.py
# @Software: PyCharm
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
        self.feedback_type_list = {2: '内容相关',
                                   3: '视频相关',
                                   7: '系统报错',
                                   17: '闪退/卡顿/加载',
                                   10: '会员相关',
                                   1: '语言字幕',
                                   4: '音量问题',
                                   5: '一起看相关',
                                   6: '电视投屏',
                                   8: '扫描相关',
                                   22: '充值相关'}
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

    def is_first_letter_uppercase(self, s):
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
    def __assert(result_queue, type_name, data, start_Time, end_Time):
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
                    text_data["用户id:"] = str(eve_data.get('userId'))
                else:
                    text_data["用户id:"] = 'None'
                if eve_data.get('question'):
                    text_data["question:"] = eve_data.get('question')
                if eve_data.get('deviceId'):
                    text_data["deviceId:"] = eve_data.get('deviceId')
                if eve_data.get('appVersion'):
                    text_data["appVersion:"] = eve_data.get('appVersion')
                if eve_data.get('createTime'):
                    text_data["createTime:"] = eve_data.get('createTime')
                if count.feedback_details(eve_data.get('id')).get('imgUrl'):
                    text_data["imgUrl:"] = count.feedback_details(eve_data.get('id')).get('imgUrl')
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
                                      args=(result_queue, type_name, now_data, start_time, end_time,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        while not result_queue.empty():
            self.results.append(result_queue.get())

        print(self.results)

        """ 转化为飞书消息格式 """
        # print(self.results)
        all_data, IOS, Android = {}, '', ''
        for type_data in self.results:
            for k, v in type_data.items():
                txt = "------------------------------{}:{} to {}:----------------------------". \
                          format(str(k), start_time, end_time, ) + "\n"
                if len(v) != 0:
                    for v1 in v:
                        """ IOS用户 """
                        if self.is_first_letter_uppercase(v1['deviceId:']) is True:
                            IOS += str(v1) + "\n"
                        else:
                            Android += str(v1) + "\n"
                    if IOS != "":
                        ios_data = {"msg_type": "text",
                                    "content":
                                        {"text": txt + IOS}
                                }
                        print(ios_data)
                        self.webhook(url='https://open.feishu.cn/open-apis/bot/v2/hook/3b0f5a23-d5cd-45a4-9f53-033f1d62a351',
                                     data=ios_data)
                    # print("------------------------------"+Android)
                else:
                    txt = "------------------------------{}:{} to {}:----------------------------". \
                               format(str(k), start_time, end_time, ) + "\n" + "近期无反馈"
                    data = {"msg_type": "text",
                            "content":
                                {"text": txt}
                            }
                    # print(data)
                    # self.webhook("", data)

    def get_all_feed(self, hours=2):
        """ 最近X消失的反馈内容 """
        hours_data = count.count_feed(self.feedback_type_list,
                                      (self.now_time + timedelta(hours=-hours)).strftime('%Y-%m-%d %H:%M:%S'),
                                      self.now_time.strftime('%Y-%m-%d %H:%M:%S'))
        """ 今天的反馈数据 """
        today = count.count_feed(self.feedback_type_list, self.today_time[0], self.today_time[1], des="today")
        """ 昨天的反馈数据 """
        yesterday = count.count_feed(self.feedback_type_list,
                                     self.yesterday_time[0], self.yesterday_time[1], des="yesterday")
        """本周的反馈数据：截至到yesterday """
        this_week = count.count_feed(self.feedback_type_list,
                                     self.this_week[0], self.this_week[1], des="this_week")
        """上周的反馈数据 """
        last_week = count.count_feed(self.feedback_type_list,
                                     self.last_week[0], self.last_week[1], des="last_week")
        """本月的反馈 """
        this_month = count.count_feed(self.feedback_type_list,
                                      self.this_month[0], self.this_month[1], des="this_month")
        """上月的反馈 """
        last_month = count.count_feed(self.feedback_type_list,
                                      self.last_month[0], self.last_month[1], des="last_month")
        all_data = str(hours_data) + "\n" + \
                   str(today) + "\n" + \
                   str(yesterday) + "\n" + \
                   str(this_week) + "\n" + \
                   str(last_week) + "\n" + \
                   str(this_month) + "\n" + \
                   str(last_month) + "\n"

        """ 周四下午3点发送一次报告 """
        error_text = ''
        if datetime.now().weekday() == 4 and datetime.now().hour == 15:
            # self.send_webhook(all_data, self.today_time, self.today_time)
            for type_name in this_week['this_week'].keys():
                if this_week['this_week'][type_name] > int(last_week['last_week'][type_name] * 1.2):
                    error_text += '本周对比上周{}上涨的幅度超过20%：'.format(type_name) + '\n'
            for type_name in this_month['this_month'].keys():
                if this_month['this_month'][type_name] > int(last_month['last_month'][type_name] * 1.2):
                    error_text += '本月对比上月{}上涨的幅度超过20%：'.format(type) + '\n'
                else:
                    pass
            if error_text != '':
                print('')
                # self.send_webhook(error_text, self.today_time[0], self.today_time[1])

    """ 消息分发 """
    def webhook(self, url, data):
        header = {'Content-Type': 'application/json'}
        requests.post(url=url,
                      json=data, headers=header).json()


if __name__ == '__main__':
    count = FeedbackCount()
    # print(count.is_first_letter_uppercase('d'))

    """ 周一 - 周五"""
    if datetime.now().weekday() <= 5:
        """ 每隔两个小时发送一次推送；22点 - 8点发送一次 """
        if 8 < datetime.now().hour <= 22 and (datetime.now().hour % 2) == 0:
            count.get_hours_feed_info(hours=2)
        """ 每天早上8点发送一次 """
        if datetime.now().hour == 8:
            count.get_hours_feed_info(hours=2)
        else:
            pass
    else:
        if (datetime.now().hour % 8) == 0:
            count.get_hours_feed_info(hours=8)
