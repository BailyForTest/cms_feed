#!/usr/local/bin/python
# -*- coding:UTF-8 -*-
# @Project : loklok
# @Time    : 2024/7/26 17:15
# @Author  : bj
# @Email   : 475829130@qq.com
# @File    : feedback_count.py
# @Software: PyCharm

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
    def __assert(type_name, data, start_Time, end_Time):
        feed_info, text_data = {}, ''
        feed_info[type_name] = []
        if not data:
            text_data = '{}近段时间无反馈:'.format(type_name)
        else:
            for eve_data in data.get('content'):
                """ statusDesc:状态  appVersion  deviceId   region"""
                # print(eve_data)
                text_data = ""
                if eve_data.get('userId'):
                    text_data += '用户{}:'.format(str(eve_data.get('userId')))
                else:
                    text_data += '用户{}:'.format('None')
                if eve_data.get('question'):
                    text_data += eve_data.get('question')
                if eve_data.get('deviceId'):
                    text_data += eve_data.get('deviceId')
                if eve_data.get('appVersion'):
                    text_data += eve_data.get('appVersion')
                if count.feedback_details(eve_data.get('id')).get('imgUrl'):
                    text_data += count.feedback_details(eve_data.get('id')).get('imgUrl')
                if eve_data.get('createTime'):
                    text_data += eve_data.get('createTime')
                feed_info[type_name].append(text_data)
        # print(feed_info)
        FeedbackCount.webhook(feed_info, start_Time, end_Time)
        return text_data

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
        threads, results = [], []
        for type_key in self.feedback_type_list.keys():
            type_name = self.feedback_type_list[type_key]
            now_data = self.get_feedback([type_key],
                                         (self.now_time + timedelta(hours=-hours)).strftime('%Y-%m-%d %H:%M:%S'),
                                         self.now_time.strftime('%Y-%m-%d %H:%M:%S'))
            # self.__assert(des, type_name, now_data.get('content'))
            t = threading.Thread(target=FeedbackCount.__assert,
                                 name=type_name,
                                 args=(type_name, now_data,
                                       (self.now_time + timedelta(hours=-hours)).strftime('%Y-%m-%d %H:%M:%S'),
                                       self.now_time.strftime('%Y-%m-%d %H:%M:%S'),))
            threads.append(t)
            t.start()

        for thread in threads:
            thread.join()

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
        all_data = str(hours_data) + "\n" +\
                   str(today) + "\n" +\
                   str(yesterday) + "\n" + \
                   str(this_week) + "\n" + \
                   str(last_week) + "\n" + \
                   str(this_month) + "\n" + \
                   str(last_month) + "\n"

        """ 周四下午3点发送一次报告 """
        error_text = ''
        if datetime.now().weekday() == 4 and datetime.now().hour == 15:
            self.webhook(all_data, self.today_time, self.today_time)
            for type_name in this_week['this_week'].keys():
                if this_week['this_week'][type_name] > int(last_week['last_week'][type_name] * 1.2):
                    error_text += '本周对比上周{}上涨的幅度超过20%：'.format(type_name) + '\n'
            for type_name in this_month['this_month'].keys():
                if this_month['this_month'][type_name] > int(last_month['last_month'][type_name] * 1.2):
                    error_text += '本月对比上月{}上涨的幅度超过20%：'.format(type) + '\n'
                else:
                    pass
            if error_text != '':
                self.webhook(error_text, self.today_time[0], self.today_time[1])

    @staticmethod
    def webhook(feeds_info, start_Time, end_Time):
        global text
        url = 'https://open.feishu.cn/open-apis/bot/v2/hook/f6b2fd6a-5bd1-4fea-be82-5ef644e7fe5e'
        header = {'Content-Type': 'application/json'}
        if type(feeds_info) is dict:
            for k, v in feeds_info.items():
                if len(v) != 0:
                    text = "{}------------------------------{} to {}:----------------------------".\
                               format(str(k), start_Time, end_Time) + "\n"
                    for eve in v:
                        text += "\n" + str(eve) + "\n"
                else:
                    text = "{}------------------------------{} to {}:----------------------------".\
                               format(str(k), start_Time, end_Time,) + "\n" + "近期无反馈"
        else:
            text = feeds_info
        data = {"msg_type": "text",
                "content":
                    {"text": text}
                }
        resp = requests.post(url=url, json=data, headers=header).json()
        # print(resp)


if __name__ == '__main__':
    count = FeedbackCount()
    """ 周一 - 周五"""
    if datetime.now().weekday() <= 5:
        """ 每隔两个小时发送一次推送；22点 - 8点发送一次 """
        if 8 < datetime.now().hour <= 22:
            count.get_hours_feed_info(hours=2)
        """ 每天早上8点发送一次 """
        if datetime.now().hour == 8:
            count.get_hours_feed_info(hours=10)
        else:
            pass
    else:
        if (datetime.now().hour / 8) ==0:
            count.get_hours_feed_info(hours=8)



