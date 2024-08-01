# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# @Project : loklok
# @Time    : 2024/7/26 17:15
# @Author  : bj
# @Email   : 475829130@qq.com
# @File    : feedback_count.py
# @Software: PyCharm
import sched
import time

import requests

from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler


class FeedbackCount:
    def __init__(self):
        self.login_url = "https://admin-api.netpop.app/auth/backend/account/login"
        self.get_feedback_url = 'https://admin-api.netpop.app/user/behavior/backend/feedback/v2/page/0'
        self.feedback_type_list = {
                                    2: '内容相关',
                                    3: '视频相关',
                                    7: '系统报错',
                                    17: '闪退/卡顿/加载',
                                    10: '会员相关',
                                    1: '语言字幕',
                                    4: '音量问题',
                                    # 5: '一起看相关',
                                    6: '电视投屏',
                                    8: '扫描相关',
                                    22: '充值相关'
                                }

    @staticmethod
    def start_or_end(date):
        startDate = date.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        endDate = date.replace(hour=23, minute=59, second=59, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        return startDate, endDate

    # 登录-获取token
    def login_cms(self):
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/126.0.0.0 Safari/537.36'
                  }
        data = {
            "username": "testrobot",
            "password": "Testrobot9456@"
        }
        resp = requests.post(url=self.login_url, json=data, headers=header).json()
        return resp['data']

    def get_feedback(self, token, feedback_type, startDate, endDate):
        '''
        :param feedback_type:
        :param time:
            当前时间  now = datetime.now()
        :return:
        '''

        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'token': token,
                  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/126.0.0.0 Safari/537.36'
                  }

        data = {"id": "",
                "contactWay": "",
                "userId": "",
                "types": feedback_type,
                "status": "",
                "dataRange": [],
                "startDate": startDate,
                "endDate": endDate,
                "page": 0,
                "size": 200
                }

        resp = requests.post(url=self.get_feedback_url, json=data, headers=header).json()
        return resp.get('data')

    @staticmethod
    def feedback_details(feedback_id):
        url = 'https://admin-api.netpop.app/user/behavior/backend/feedback/v2/detail/{}'.format(feedback_id)
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'token': token,
                  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/126.0.0.0 Safari/537.36'
                  }

        resp = requests.get(url=url, headers=header).json()
        return resp.get('data')

    def __assert(self, des, type_name, data):
        global text_data
        if des == 'two_hours':
            if not data:
                text_data = '{}近两个小时无反馈:'.format(type_name)
            else:
                text_data = '{}：'.format(type_name) + '\n'
                for eve_data in data:
                    # print(eve_data)
                    if count.feedback_details(eve_data.get('id')).get('imgUrl'):
                        text_data += '用户{}:'.format(eve_data.get('userId')) + eve_data.get(
                            'question') + count.feedback_details(
                            eve_data.get('id')).get('imgUrl') + eve_data.get('createTime') + '\n'
                    else:
                        text_data += '用户{}:'.format(eve_data.get('userId')) + eve_data.get('question') + str(
                            eve_data.get('createTime')) + '\n'
            print(text_data)
        else:
            if not data:
                text_data = '{}{}无反馈'.format(des, type_name)
            else:
                pass
        return text_data

    def weebhook(self, data):
        url = 'https://open.feishu.cn/open-apis/bot/v2/hook/cdc47192-c4dd-4b38-b530-bd6063a60c48'
        header = {'Content-Type': 'application/json'}
        data = {"msg_type": "text",
                "content":
                    {"text": data}
                }
        resp = requests.post(url=url, json=data, headers=header).json()
        print(resp)

    def run(self, feedback_type_list, startDate, endDate, des='two_hours', input_text=""):
        count_data = {des: {"all_count": 0}}
        for type in feedback_type_list.keys():
            now_data = FeedbackCount().get_feedback(token, [type], startDate, endDate)
            print(now_data)
            count_data[des]['all_count'] += now_data.get('totalElements')
            type_name = feedback_type_list[type]
            count_data[des][type_name] = now_data.get('totalElements')
            input_text += self.__assert(des, type_name, now_data.get('content')) + '\n'
        print('{}合计反馈数：{}'.format(des, count_data))
        # print("----------------"+input_text)
        return count_data, input_text

    def get_data(self):
        now = datetime.now()
        # 获取最近两个小时的反馈的数据
        # print(now.strftime('%Y-%m-%d %H:%M:%S'))
        # print((now + timedelta(hours=-2)).strftime('%Y-%m-%d %H:%M:%S'))
        two_hours = count.run(self.feedback_type_list,
                              (now + timedelta(hours=-4)).strftime('%Y-%m-%d %H:%M:%S'),
                              now.strftime('%Y-%m-%d %H:%M:%S'))

        # 今天的反馈数
        today = count.run(self.feedback_type_list,
                          self.start_or_end(datetime.now())[0],
                          self.start_or_end(datetime.now())[1],
                          des="today")

        # 昨天的反馈数
        yesterday = count.run(self.feedback_type_list,
                              self.start_or_end(datetime.now() + timedelta(days=-1))[0],
                              self.start_or_end(datetime.now() + timedelta(days=-1))[1],
                              des="yesterday")

        # 以今天为维度，本周的数据
        # print(count.start_or_end(datetime.now() + timedelta(days=-6))[0])
        # print(count.start_or_end(datetime.now())[1])
        week = count.run(self.feedback_type_list,
                         self.start_or_end(datetime.now() + timedelta(days=-6))[0],
                         self.start_or_end(datetime.now())[1],
                         des="week")

        # 上周的数据
        last_week = count.run(self.feedback_type_list,
                              self.start_or_end(datetime.now() + timedelta(days=-13))[0],
                              self.start_or_end(datetime.now() + timedelta(days=-7))[1],
                              des="last_week")

        # 获取本月时间段
        first_of_month = datetime(year=now.year, month=now.month, day=1)
        last_of_month = first_of_month + timedelta(days=31) - timedelta(days=first_of_month.day)
        month = count.run(
            self.feedback_type_list,
            self.start_or_end(first_of_month)[0],
            self.start_or_end(last_of_month)[1],
            des="month")

        # 获取上月时间段
        last_first_of_month = datetime(year=now.year, month=now.month - 1, day=1)
        last_last_of_month = last_first_of_month + timedelta(days=30) - timedelta(days=first_of_month.day)
        last_month = count.run(
            self.feedback_type_list,
            self.start_or_end(last_first_of_month)[0],
            self.start_or_end(last_last_of_month)[1],
            des="last_month")

        # 判断今天上涨浮动
        error_text = ''
        for type in today[0]['today'].keys():
            if today[0]['today'][type] > int(yesterday[0]['yesterday'][type] * 1.2):
                error_text += '今日对比昨日{}上涨的幅度超过20%：'.format(type) + '\n'
        for type in week[0]['week'].keys():
            if week[0]['week'][type] > int(last_week[0]['last_week'][type] * 1.2):
                error_text += '本周对比上周{}上涨的幅度超过20%：'.format(type) + '\n'
        for type in month[0]['month'].keys():
            if month[0]['month'][type] > int(last_month[0]['last_month'][type] * 1.2):
                error_text += '本月对比上月{}上涨的幅度超过20%：'.format(type) + '\n'
            else:
                pass

        count.weebhook(
            str((now + timedelta(hours=-2)).strftime('%Y-%m-%d %H:%M:%S')) + '---' + str(
                now.strftime('%Y-%m-%d %H:%M:%S')) + "\n"
            + two_hours[1] + "\n"

            # + str('---------------------数据----------------------') + "\n"
            # + str(today[0]) + "\n"
            # + str(yesterday[0]) + "\n"
            # + str(week[0]) + "\n"
            # + str(last_week[0]) + "\n"
            # + str(month[0]) + "\n"
            # + str(last_month[0]) + "\n\n"
            #
            # + str('---------------------注意----------------------') + "\n"
            # + error_text
        )

    # 'region': '伊拉克'
    def get_for_region(self, token):
        count_data = {'data': {"all_count": 0}}
        for type in self.feedback_type_list.keys():
            now_data = FeedbackCount().get_feedback(token, [type],  self.start_or_end(datetime.now() + timedelta(days=-12))[0], self.start_or_end(datetime.now())[1])
            # print(now_data)
            count_data['data']['all_count'] += now_data.get('totalElements')
            type_name = self.feedback_type_list[type]
            count_data['data'][type_name] = {}
            count_data['data'][type_name]['count'] = now_data.get('totalElements')
            for region_data in now_data.get('content'):
                # print(region_data)
                region = self.feedback_details(region_data.get('id')).get('region')
                if region not in count_data['data'][type_name].keys():
                    count_data['data'][type_name][region] = 1
                else:
                    count_data['data'][type_name][region] += 1
                print(count_data)
        print(count_data)


if __name__ == '__main__':
    count = FeedbackCount()
    token = count.login_cms()
    # token = '27108f23-ee16-43ad-9f70-05acffe98367'

    # count.get_for_region(token)
    interval = 60*60*2  # 间隔5秒
    while True:
        count.get_data()
        time.sleep(interval)

