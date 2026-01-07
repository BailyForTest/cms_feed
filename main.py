#!/usr/local/bin/python
# -*- coding: UTF-8 -*-
# @Project : loklok
# @Time    : 2024/11/13 17:00
# @Author  : bj
# @Email   : 475829130@qq.com
# @File    : loklok_feedback_count.py
# @Software: PyCharm
"""
Loklok 反馈统计系统
所有统计信息都根据应用名和渠道组进行统计
支持实时反馈统计和周汇总报告功能
"""
import json
import threading
from typing import Dict, Tuple, List

import requests
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import yaml
import os


class FeedbackCount(threading.Thread):
    """
    反馈统计类
    支持按应用名和渠道组统计反馈数据
    提供实时反馈统计和周汇总报告功能
    """

    # 飞书机器人Webhook配置
    WEBHOOK_URLS = {
        'Android': 'https://open.feishu.cn/open-apis/bot/v2/hook/cdc47192-c4dd-4b38-b530-bd6063a60c48',
        # 'Android': 'https://open.feishu.cn/open-apis/bot/v2/hook/f6b2fd6a-5bd1-4fea-be82-5ef644e7fe5e',
        'iOS': 'https://open.feishu.cn/open-apis/bot/v2/hook/3b0f5a23-d5cd-45a4-9f53-033f1d62a351',
        # 'iOS': 'https://open.feishu.cn/open-apis/bot/v2/hook/f6b2fd6a-5bd1-4fea-be82-5ef644e7fe5e',
        "Count": "https://open.feishu.cn/open-apis/bot/v2/hook/6954f098-de98-49e3-8640-f04ae47161ba"
    }

    # API配置
    FEEDBACK_TAB_CONFIG_URL = "https://admin-api.netpop.app/user/behavior/backend/feedback/tab/config"
    FEEDBACK_LIST_URL = "https://admin-api.netpop.app/cms/backend/issues/type/list"
    CMS_LOGIN_URL = "https://admin-api.netpop.app/auth/backend/account/login"
    FEEDBACK_URL = 'https://admin-api.netpop.app/user/behavior/backend/feedback/v2/page/0'
    TRANSLATE_URL = "https://admin-api.netpop.app/third/backend/openai/translate"

    # 已解决、未解决问题数的接口URL
    CHANNEL_CONFIG_URL = "https://admin-api.netpop.app/user/behavior/backend/feedback/issue/config"
    CATEGORY_LIST_URL = "https://admin-api.netpop.app/cms/backend/issues/category/queryByPage"
    SUBCATEGORY_LIST_URL = "https://admin-api.netpop.app/cms/backend/issues/queryByPage"

    # HTTP请求头
    HEADERS = {
        'Content-Type': 'application/json;charset=UTF-8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }

    def __init__(self):
        """初始化反馈统计实例"""
        super().__init__()
        self.token = self.login_cms()
        self.now = datetime.now()
        self.results = []
        self.feedback_tab_config = self.get_feedback_tab_config()
        self.feedback_list = self.get_feedback_list()
        # print(self.feedback_tab_config)
        # print(self.feedback_list)

    @staticmethod
    def get_time_range(hours=0, days=0):
        """
        获取时间范围
        :param hours: 小时数
        :param days: 天数
        :return: (开始时间, 结束时间)
        """
        start = datetime.now() - timedelta(hours=hours, days=days)
        return (
            start.strftime('%Y-%m-%d %H:%M:%S'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    def login_cms(self):
        """
        登录CMS系统获取token
        :return: token字符串
        """
        try:
            data = {"username": "testrobot", "password": "Testrobot9456@"}
            resp = requests.post(self.CMS_LOGIN_URL, json=data, headers=self.HEADERS).json()
            token = resp.get('data', '')
            if not token:
                print("⚠️  获取CMS token失败")
            return token
        except Exception as e:
            print(f"❌ 登录CMS失败: {str(e)}")
            return ""

    def get_feedback_tab_config(self):
        """
        获取反馈页面的导航栏配置
        :return: 配置列表
        """
        try:
            if not self.token:
                print("❌ 未获取到CMS token，无法获取反馈配置")
                return []

            headers = {**self.HEADERS, 'token': self.token}
            resp = requests.get(self.FEEDBACK_TAB_CONFIG_URL, headers=headers).json()
            return resp.get('data', [])
        except Exception as e:
            print(f"❌ 获取反馈配置失败: {str(e)}")
            return []

    def get_feedback_list(self):
        """
        获取反馈类型列表，按应用-渠道组分组
        :return: 反馈类型列表
        """
        list_data = []
        try:
            if not self.token:
                print("❌ 未获取到CMS token，无法获取反馈类型")
                return list_data

            headers = {**self.HEADERS, 'token': self.token}
            for tab in self.feedback_tab_config:
                app_name = tab.get('appName')
                client_group = tab.get('clientGroupCode')

                if not app_name or not client_group:
                    continue

                data = {"appName": app_name, "clientGroup": client_group}
                # print(data)
                resp = requests.get(self.FEEDBACK_LIST_URL, params=data, headers=headers).json()
                # print(resp)

                if resp.get('data') is not None:
                    feedback_types = {item['id']: item['name'] for item in resp['data']}
                    tab['FEEDBACK_TYPES'] = feedback_types
                    # print(tab['FEEDBACK_TYPES'])
                    list_data.append(tab)
            return list_data
        except Exception as e:
            print(f"❌ 获取反馈类型列表失败: {str(e)}")
            return list_data

    def get_feedback(self, appName, clientGroup, feedback_type, start_date, end_date, page=0, size=200):
        """
        获取反馈数据
        :param appName: 应用名称
        :param clientGroup: 渠道组编码
        :param feedback_type: 反馈类型列表
        :param start_date: 开始时间
        :param end_date: 结束时间
        :param page: 页码
        :param size: 每页大小
        :return: 反馈数据
        """
        try:
            if not self.token:
                print("❌ 未获取到CMS token，无法获取反馈数据")
                return {}

            headers = {**self.HEADERS, 'token': self.token}
            data = {
                "appName": appName,
                "clientGroup": clientGroup,
                "types": feedback_type,
                "startDate": start_date,
                "endDate": end_date,
                "page": page,
                "size": size
            }
            resp = requests.post(self.FEEDBACK_URL, json=data, headers=headers).json()
            return resp.get('data', {})
        except Exception as e:
            print(f"❌ 获取反馈数据失败: {str(e)}")
            return {}

    def get_feedback_count_only(self, appName, clientGroup, feedback_type, start_date, end_date):
        """
        仅获取反馈数量（优化版，用于周汇总统计）
        :param appName: 应用名称
        :param clientGroup: 渠道组编码
        :param feedback_type: 反馈类型列表
        :param start_date: 开始时间
        :param end_date: 结束时间
        :return: 反馈数量
        """
        try:
            if not self.token:
                print("❌ 未获取到CMS token，无法获取反馈数据")
                return 0

            headers = {**self.HEADERS, 'token': self.token}
            data = {
                "appName": appName,
                "clientGroup": clientGroup,
                "types": feedback_type,
                "startDate": start_date,
                "endDate": end_date,
                "page": 0,
                "size": 1  # 只需要获取总数，所以size设为1
            }
            resp = requests.post(self.FEEDBACK_URL, json=data, headers=headers).json()
            data_result = resp.get('data', {})
            return data_result.get('totalElements', 0) if data_result else 0
        except Exception as e:
            print(f"❌ 获取反馈数量失败: {str(e)}")
            return 0

    def get_feedback_detail(self, feedback_id):
        """
        获取反馈详情
        :param feedback_id: 反馈ID
        :return: 反馈详情
        """
        try:
            if not self.token:
                print("❌ 未获取到CMS token，无法获取反馈详情")
                return {}

            url = f'https://admin-api.netpop.app/user/behavior/backend/feedback/v2/detail/{feedback_id}'
            headers = {**self.HEADERS, 'token': self.token}
            resp = requests.get(url, headers=headers).json()
            return resp.get('data', {})
        except Exception as e:
            print(f"❌ 获取反馈详情失败: {str(e)}")
            return {}

    def translate_text(self, text):
        """
        翻译文本
        :param text: 待翻译文本
        :return: 翻译结果
        """
        try:
            if not self.token:
                print("❌ 未获取到CMS token，无法翻译文本")
                return text

            if not text:
                return ""

            headers = {
                **self.HEADERS,
                "token": self.token,
                "Content-Type": "text/plain"
            }
            params = {"lan": "中文"}
            response = requests.post(self.TRANSLATE_URL, data=text.encode('utf-8'),
                                     headers=headers, params=params)
            return response.json().get("data", text)
        except Exception as e:
            print(f"⚠️  翻译文本失败，返回原文: {str(e)}")
            return text

    def format_description(self, text):
        """
        格式化问题描述（添加翻译）
        :param text: 问题描述
        :return: 格式化后的描述
        """
        if not text:
            return ""
        translated = self.translate_text(text)
        return f"\n**原文**：{text}\n**译文**：{translated}"

    @staticmethod
    def format_images(img_url):
        """
        格式化图片URL
        :param img_url: 图片URL字符串
        :return: 格式化后的URL列表
        """
        if not img_url:
            return ""
        return img_url.strip('[]').replace('"', "").replace(',', "\n")

    def get_feedback_value_from_json_str(self, json_str) -> str:
        """
        从 JSON 格式数据中提取 title=反馈描述 的 value（新增参数校验，解决 None 报错）
        :param json_str: 原始 JSON 数据（支持 str/bytes/bytearray，允许为 None）
        :return: 匹配的 value（参数非法/解析失败/无匹配均返回空字符串）
        """
        # 初始化返回值（确保始终返回字符串）
        feedback_value = ""

        # ---------------------- 关键：参数前置校验 ----------------------
        # 1. 处理参数为 None 的情况
        if json_str is None:
            print("❌ 错误：传入的 JSON 数据为 None，请检查数据来源")
            return feedback_value

        # 2. 处理参数类型不合法（必须是 str/bytes/bytearray）
        valid_types = (str, bytes, bytearray)
        if not isinstance(json_str, valid_types):
            print(f"❌ 错误：传入的 JSON 数据类型不合法（当前类型：{type(json_str)}），仅支持 {valid_types}")
            return feedback_value

        # ---------------------- 原有逻辑（JSON 解析 + 提取 value） ----------------------
        try:
            # 解析 JSON 数据（支持 str/bytes/bytearray）
            data_list = json.loads(json_str)

            # 验证解析结果是列表（避免 JSON 是字典/其他结构）
            if not isinstance(data_list, list):
                print("❌ 解析结果不是列表，无法提取数据")
                return feedback_value

            # 提取 title=反馈描述 的 value（全链路防护 None）
            match_gen = (
                item.get("value", "")  # 无 value 键 → 返回空字符串
                for item in data_list
                if item.get("title") == "问题描述" or item.get("title") == "反馈描述" or item.get("title") == "请输入剧集/电影名称" # 无 title 键 → 不匹配
            )
            feedback_value = next(match_gen, "")  # 无匹配项 → 返回空字符串

        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败（格式错误）：{str(e)}")
        except Exception as e:
            print(f"❌ 处理失败：{str(e)}")

        # 最终兜底：强制转为字符串（避免极端情况返回 None）
        return str(feedback_value) if feedback_value is not None else ""

    def process_feedback_type(self, app_name, client_group, feedback_type_id, feedback_type_name, start_time, end_time):
        """
        处理单个应用-渠道组-反馈类型的数据
        :param app_config: 应用配置
        :param feedback_type_id: 反馈类型ID
        :param feedback_type_name: 反馈类型名称
        :param start_time: 开始时间
        :param end_time: 结束时间
        :return: 处理结果
        """
        try:
            # print(app_config)
            appName = app_name
            clientGroup = client_group
            # clientGroupName = app_config.get('clientGroupName')

            if not appName or not clientGroup:
                print("❌ 应用配置不完整")
                return None

            # 获取反馈数据
            data = self.get_feedback(appName, clientGroup, [feedback_type_id], start_time, end_time)

            if not data or not data.get('content'):
                return {
                    'appName': appName,
                    'clientGroup': clientGroup,
                    # 'clientGroupName': clientGroupName,
                    'feedback_type': feedback_type_name,
                    'feedback_type_id': feedback_type_id,
                    'count': 0,
                    'items': []
                }

            # 处理反馈详情
            processed = []
            for item in data['content']:
                detail = self.get_feedback_detail(item['id'])
                text_data = {
                    "用户ID": str(item.get('userId', 'None')),
                    "IP地区": item.get('region', detail.get('region', '')),
                    "IP地址": item.get('ipAddress', detail.get('ipAddress', '')),
                    "版本渠道": item.get('appName', ''),
                    "问题描述": self.format_description(detail.get('question', '')),
                    "设备ID": item.get('deviceId', ''),
                    "版本信息": item.get('appVersion', ''),
                    "反馈时间": item.get('createTime', ''),
                    "反馈截图": self.format_images(detail.get('imgUrl', ''))
                }
                if detail.get('templateInfo') != '' and detail.get('templateInfo') is not None:
                    print(item['id'])
                    data = detail.get('templateInfo')
                    # print("===================="+data)
                    feed_detail = self.get_feedback_value_from_json_str(data)
                    print("================="+feed_detail)
                    text_data.update({"问题描述": self.format_description(feed_detail)})
                processed.append(text_data)

            return {
                'appName': appName,
                'clientGroup': clientGroup,
                # 'clientGroupName': clientGroupName,
                'feedback_type': feedback_type_name,
                'feedback_type_id': feedback_type_id,
                'count': len(processed),
                'items': processed
            }
        except Exception as e:
            print(f"❌ 处理反馈数据失败: {str(e)}")
            return None

    def process_feedback_count_only(self, app_name, client_group, feedback_type_id, feedback_type_name, start_time, end_time):
        """
        仅处理反馈数量（优化版，用于周汇总统计）
        :param app_name: 应用名称
        :param client_group: 渠道组编码
        :param feedback_type_id: 反馈类型ID
        :param feedback_type_name: 反馈类型名称
        :param start_time: 开始时间
        :param end_time: 结束时间
        :return: 处理结果（仅包含数量）
        """
        try:
            if not app_name or not client_group:
                print("❌ 应用配置不完整")
                return None

            # 仅获取反馈数量
            count = self.get_feedback_count_only(app_name, client_group, [feedback_type_id], start_time, end_time)

            return {
                'appName': app_name,
                'clientGroup': client_group,
                'feedback_type': feedback_type_name,
                'feedback_type_id': feedback_type_id,
                'count': count
            }
        except Exception as e:
            print(f"❌ 处理反馈数量失败: {str(e)}")
            return None

    def send_to_feishu(self, data=None, platform=None, start_time=None, end_time=None, type=None, title=None):
        """
        发送数据到飞书
        :param data: 要发送的数据
        :param platform: 平台（Android/iOS）
        :param start_time: 开始时间
        :param end_time: 结束时间
        """
        try:
            if not data:
                return
            url = self.WEBHOOK_URLS.get(platform)
            if not url:
                print(f"❌ 未配置{platform}平台的飞书Webhook URL")
                return

            # 添加时间段信息到标题
            if type is None:
                url = self.WEBHOOK_URLS.get(platform)
                time_range = f"{start_time} 至 {end_time}"
                title = f"用户反馈 ({time_range})"
            elif type == "day_count":
                url = self.WEBHOOK_URLS.get("Count")
                title = f"{title} )"
            elif type == "week_count":
                url = self.WEBHOOK_URLS.get("Count")
                title = f"{title} )"
            else:
                url = self.WEBHOOK_URLS.get("Count")
                title = f"{end_time} 用户反馈 ({type})"
            # 使用飞书markdown格式
            markdown_content = f"{data}"

            card = {
                "msg_type": "interactive",
                "card": {
                    "elements": [{
                        "tag": "div",
                        "text": {
                            "content": markdown_content,
                            "tag": "lark_md"
                        }
                    }],
                    "header": {
                        "title": {
                            "content": title,
                            "tag": "plain_text"
                        }
                    }
                }
            }
            response = requests.post(url, json=card)
            if response.status_code != 200:
                print(f"❌ 飞书消息发送失败: {response.text}")
            else:
                print(f"✅ 飞书消息发送成功")
        except Exception as e:
            print(f"❌ 发送飞书消息失败: {str(e)}")

    def get_recent_feedback(self, hours=2):
        """
        获取最近几小时的反馈
        :param hours: 小时数
        """
        try:
            print(f"⏳ 开始获取最近{hours}小时的反馈数据...")

            if not self.feedback_list:
                print("❌ 未获取到反馈类型列表，无法统计反馈数据")
                return

            start_time, end_time = self.get_time_range(hours=hours)

            # 准备所有需要处理的任务
            tasks = []
            for app_config in self.feedback_list:
                # print(app_config)
                feedback_types = app_config.get('FEEDBACK_TYPES', {})
                for ft_id, ft_name in feedback_types.items():
                    tasks.append((app_config['appName'], app_config['clientGroupCode'], ft_id, ft_name, start_time, end_time))
            # print(tasks)

            if not tasks:
                print("⚠️  没有需要处理的反馈类型")
                return

            # 使用线程池处理所有任务
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.process_feedback_type, *task) for task in tasks]
                self.results = [future.result() for future in futures if future.result() is not None]
            print(self.results)

            # 按应用和渠道组分类数据
            app_channel_data = {}
            for result in self.results:
                if result['count'] == 0:
                    continue

                key = f"{result['appName']}_{result['clientGroup']}"
                if key not in app_channel_data:
                    app_channel_data[key] = {
                        'appName': result['appName'],
                        'clientGroup': result['clientGroup'],
                        # 'clientGroupName': result['clientGroupName'],
                        'total_count': 0,
                        'types': {},
                        'items': []
                    }

                # 添加到对应类型
                type_key = f"{result['feedback_type_id']}_{result['feedback_type']}"
                app_channel_data[key]['types'][type_key] = {
                    'id': result['feedback_type_id'],
                    'name': result['feedback_type'],
                    'count': result['count']
                }
                app_channel_data[key]['total_count'] += result['count']
                app_channel_data[key]['items'].extend(result['items'])
                print(app_channel_data)

            # 按应用和渠道组发送消息
            for key, data in app_channel_data.items():
                # 构建消息内容
                content = f"**应用名称**: {data['appName']}\n"
                content += f"**渠道组**: {data['clientGroup']}\n"
                content += f"**总反馈数**: {data['total_count']}\n\n"

                content += "**分类统计**:\n"
                for type_info in data['types'].values():
                    content += f"- **{type_info['name']}**: {type_info['count']}条\n"

                content += "\n**详细反馈**:\n"
                for item in data['items']:
                    # 加粗关键字段
                    item_content = "\n".join(
                        f"**{k}**: {v}" if k in ["问题描述", "反馈类型"]
                        else f"{k}: {v}"
                        for k, v in item.items()
                    ) + "\n\n"
                    content += item_content

                # 发送消息，根据应用名选择平台
                platform = 'iOS' if 'iOS' in data['appName'] or 'ios' in data['appName'] else 'Android'
                self.send_to_feishu(content, platform, start_time, end_time)

            print(f"✅ 最近{hours}小时反馈统计完成")

        except Exception as e:
            print(f"❌ 获取最近反馈失败: {str(e)}")

    def _calc_growth_rate(self, this_count, last_count):
        """
        辅助函数：计算环比增长率，返回格式化的环比字符串
        :param this_count: 本周数量
        :param last_count: 上周数量
        :return: 格式化环比字符串
        """
        if last_count > 0:
            change_rate = ((this_count - last_count) / last_count) * 100
            # 统一格式：增长显示+，下降显示-，保留1位小数
            if change_rate >= 0:
                return f"+{change_rate:.1f}%"
            else:
                return f"{change_rate:.1f}%"
        elif this_count > 0 and last_count == 0:
            return "上周无数据，本周新增"
        elif this_count == 0 and last_count > 0:
            return "本周无数据，上周留存"
        else:
            return "无变化"

    def get_weekly_summary(self):
        """获取周汇总数据（优化版：适配飞书格式，一行对比本周/上周，展示环比增长）"""
        try:
            print("⏳ 开始生成周汇总报告...")

            if not self.feedback_list:
                print("❌ 未获取到反馈类型列表，无法生成周汇总报告")
                return

            # 基准时间规范化为当天上午10点
            standard_now = self.now.replace(hour=10, minute=0, second=0, microsecond=0)
            this_week_end = standard_now.strftime('%Y-%m-%d %H:%M:%S')
            this_week_start = (standard_now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
            last_week_start = (standard_now - timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S')
            last_week_end = (standard_now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

            print(this_week_start)
            print(this_week_end)
            print(last_week_start)
            print(last_week_end)

            # 准备所有需要处理的任务
            this_week_tasks = []
            last_week_tasks = []

            for app_config in self.feedback_list:
                feedback_types = app_config.get('FEEDBACK_TYPES', {})
                for ft_id, ft_name in feedback_types.items():
                    this_week_tasks.append((app_config['appName'], app_config['clientGroupCode'], ft_id, ft_name,
                                            this_week_start, this_week_end))
                    last_week_tasks.append((app_config['appName'], app_config['clientGroupCode'], ft_id, ft_name,
                                            last_week_start, last_week_end))

            if not this_week_tasks:
                print("⚠️  没有需要处理的反馈类型")
                return

            # 使用线程池处理所有任务
            with ThreadPoolExecutor() as executor:
                # 处理本周数据（仅统计数量）
                this_week_futures = [executor.submit(self.process_feedback_count_only, *task) for task in
                                     this_week_tasks]
                this_week_results = [future.result() for future in this_week_futures if future.result() is not None]

                # 处理上周数据（仅统计数量）
                last_week_futures = [executor.submit(self.process_feedback_count_only, *task) for task in
                                     last_week_tasks]
                last_week_results = [future.result() for future in last_week_futures if future.result() is not None]

            # 按应用和渠道组分类汇总数据
            summary_data = {}

            # 处理本周数据
            for result in this_week_results:
                key = f"{result['appName']}_{result['clientGroup']}"
                if key not in summary_data:
                    summary_data[key] = {
                        'appName': result['appName'],
                        'clientGroup': result['clientGroup'],
                        'this_week': {'total': 0, 'types': {}},
                        'last_week': {'total': 0, 'types': {}}
                    }

                summary_data[key]['this_week']['total'] += result['count']
                summary_data[key]['this_week']['types'][result['feedback_type']] = result['count']

            # 处理上周数据
            for result in last_week_results:
                key = f"{result['appName']}_{result['clientGroup']}"
                if key not in summary_data:
                    continue

                summary_data[key]['last_week']['total'] += result['count']
                summary_data[key]['last_week']['types'][result['feedback_type']] = result['count']

            # 统计有数据的应用渠道组数量
            valid_data_count = 0

            # 构建汇总消息（适配飞书格式）
            for key, data in summary_data.items():
                # 检查本周和上周的总反馈数，如果都为0则跳过
                if data['this_week']['total'] == 0 and data['last_week']['total'] == 0:
                    continue

                # 1. 基础信息（飞书加粗格式）
                # content = f"**应用名称**: {data['appName']}\n"
                content = f"**渠道组**: {data['clientGroup']}\n"

                # 2. 标题：本周和上周统计对比
                content += "本周和上周统计对比:\n"

                # 3. 一级：总反馈数 一行对比 + 环比
                last_total = data['last_week']['total']
                this_total = data['this_week']['total']
                total_growth = self._calc_growth_rate(this_total, last_total)
                # 按要求格式拼接：上周总反馈数: X，本周总反馈数：Y，环比XXX%
                content += f"- 上周总反馈数: {last_total}，本周总反馈数：{this_total}，环比 {total_growth}\n"

                # 4. 二级：各反馈类型 缩进对比 + 环比（去重所有反馈类型）
                # 合并本周和上周的所有反馈类型，避免遗漏
                all_feedback_types = set(
                    list(data['this_week']['types'].keys()) + list(data['last_week']['types'].keys()))
                for type_name in all_feedback_types:
                    last_type_count = data['last_week']['types'].get(type_name, 0)
                    this_type_count = data['this_week']['types'].get(type_name, 0)
                    # 跳过本周和上周都为0的类型
                    if last_type_count == 0 and this_type_count == 0:
                        continue
                    # 计算该类型环比
                    type_growth = self._calc_growth_rate(this_type_count, last_type_count)
                    # 二级缩进（4个空格，适配飞书排版），按要求格式拼接
                    content += f"  - 上周{type_name}: {last_type_count}条，本周{type_name}: {this_type_count}条，环比 {type_growth}\n"

                # 5. 发送飞书消息
                platform = 'iOS' if 'iOS' in data['appName'] or 'ios' in data['appName'] else 'Android'
                self.send_to_feishu(content, platform, this_week_start, this_week_end, type="周报")
                valid_data_count += 1

            if valid_data_count == 0:
                print("✅ 本周和上周均无反馈数据，未发送任何周汇总报告")
            else:
                print(f"✅ 周汇总报告生成完成，共发送 {valid_data_count} 条报告")

        except Exception as e:
            print(f"❌ 生成周汇总报告失败: {str(e)}")

    def get_daily_summary(self):
        """获取周汇总数据（优化版：适配飞书格式，一行对比本周/上周，展示环比增长）"""
        try:
            print("⏳ 开始生成日汇总报告...")

            if not self.feedback_list:
                print("❌ 未获取到反馈类型列表，无法生成日汇总报告")
                return

            # 基准时间规范化为当天上午10点
            standard_now = self.now.replace(hour=10, minute=0, second=0, microsecond=0)
            this_week_end = standard_now.strftime('%Y-%m-%d %H:%M:%S')
            this_week_start = (standard_now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
            last_week_start = (standard_now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
            last_week_end = (standard_now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

            print(this_week_start)
            print(this_week_end)
            print(last_week_start)
            print(last_week_end)

            # 准备所有需要处理的任务
            this_week_tasks = []
            last_week_tasks = []

            for app_config in self.feedback_list:
                feedback_types = app_config.get('FEEDBACK_TYPES', {})
                for ft_id, ft_name in feedback_types.items():
                    this_week_tasks.append((app_config['appName'], app_config['clientGroupCode'], ft_id, ft_name,
                                            this_week_start, this_week_end))
                    last_week_tasks.append((app_config['appName'], app_config['clientGroupCode'], ft_id, ft_name,
                                            last_week_start, last_week_end))

            if not this_week_tasks:
                print("⚠️  没有需要处理的反馈类型")
                return

            # 使用线程池处理所有任务
            with ThreadPoolExecutor() as executor:
                # 处理本周数据（仅统计数量）
                this_week_futures = [executor.submit(self.process_feedback_count_only, *task) for task in
                                     this_week_tasks]
                this_week_results = [future.result() for future in this_week_futures if future.result() is not None]

                # 处理上周数据（仅统计数量）
                last_week_futures = [executor.submit(self.process_feedback_count_only, *task) for task in
                                     last_week_tasks]
                last_week_results = [future.result() for future in last_week_futures if future.result() is not None]

            # 按应用和渠道组分类汇总数据
            summary_data = {}

            # 处理本周数据
            for result in this_week_results:
                key = f"{result['appName']}_{result['clientGroup']}"
                if key not in summary_data:
                    summary_data[key] = {
                        'appName': result['appName'],
                        'clientGroup': result['clientGroup'],
                        'this_week': {'total': 0, 'types': {}},
                        'last_week': {'total': 0, 'types': {}}
                    }

                summary_data[key]['this_week']['total'] += result['count']
                summary_data[key]['this_week']['types'][result['feedback_type']] = result['count']

            # 处理上周数据
            for result in last_week_results:
                key = f"{result['appName']}_{result['clientGroup']}"
                if key not in summary_data:
                    continue

                summary_data[key]['last_week']['total'] += result['count']
                summary_data[key]['last_week']['types'][result['feedback_type']] = result['count']

            # 统计有数据的应用渠道组数量
            valid_data_count = 0

            # 构建汇总消息（适配飞书格式）
            for key, data in summary_data.items():
                # 检查本周和上周的总反馈数，如果都为0则跳过
                if data['this_week']['total'] == 0 and data['last_week']['total'] == 0:
                    continue

                # 1. 基础信息（飞书加粗格式）
                # content = f"**应用名称**: {data['appName']}\n"
                content = f"**渠道组**: {data['clientGroup']}\n"

                # 2. 标题：本周和上周统计对比
                content += "今天和昨天统计对比:\n"

                # 3. 一级：总反馈数 一行对比 + 环比
                last_total = data['last_week']['total']
                this_total = data['this_week']['total']
                total_growth = self._calc_growth_rate(this_total, last_total)
                # 按要求格式拼接：上周总反馈数: X，本周总反馈数：Y，环比XXX%
                content += f"- 昨天总反馈数: {last_total}，今天总反馈数：{this_total}，环比 {total_growth}\n"

                # 4. 二级：各反馈类型 缩进对比 + 环比（去重所有反馈类型）
                # 合并本周和上周的所有反馈类型，避免遗漏
                all_feedback_types = set(
                    list(data['this_week']['types'].keys()) + list(data['last_week']['types'].keys()))
                for type_name in all_feedback_types:
                    last_type_count = data['last_week']['types'].get(type_name, 0)
                    this_type_count = data['this_week']['types'].get(type_name, 0)
                    # 跳过本周和上周都为0的类型
                    if last_type_count == 0 and this_type_count == 0:
                        continue
                    # 计算该类型环比
                    type_growth = self._calc_growth_rate(this_type_count, last_type_count)
                    # 二级缩进（4个空格，适配飞书排版），按要求格式拼接
                    content += f"  - 昨天{type_name}: {last_type_count}条，今天{type_name}: {this_type_count}条，环比 {type_growth}\n"

                # 5. 发送飞书消息
                platform = 'iOS' if 'iOS' in data['appName'] or 'ios' in data['appName'] else 'Android'
                self.send_to_feishu(content, platform, this_week_start, this_week_end,  type="日报")
                valid_data_count += 1

            if valid_data_count == 0:
                print("✅ 今天和昨天均无反馈数据，未发送任何周汇总报告")
            else:
                print(f"✅ 日汇总报告生成完成，共发送 {valid_data_count} 条报告")

        except Exception as e:
            print(f"❌ 生成日汇总报告失败: {str(e)}")

    ####--------------------获取已解决/未解决数模块
    def get_channel_config(self):
        """
        第一步：获取所有渠道配置信息
        返回：渠道配置列表（失败返回空列表）
        """
        try:
            headers = {**self.HEADERS, 'token': self.token}
            response = requests.get(self.CHANNEL_CONFIG_URL, headers=headers, timeout=30)
            response.raise_for_status()  # 抛出HTTP错误
            result = response.json()

            if result.get("code") == "00000":
                return result["data"]
            else:
                return []
        except Exception as e:
            return []

    def get_category_details(self, app_name, client_group, platform_type):
        """
        第二步：根据渠道信息获取大类问题详情
        参数：
            app_name: 应用名称（如LOKLOK）
            client_group: 客户端分组编码（如LOKLOK）
            platform_type: 平台类型（如APP）
        返回：大类列表（失败返回空列表）
        """
        params = {
            "appName": app_name,
            "clientGroup": client_group,
            "platformType": platform_type,
            "page": 0,
            "size": 100  # 设为足够大的值，确保获取所有大类
        }
        try:
            headers = {**self.HEADERS, 'token': self.token}
            response = requests.get(self.CATEGORY_LIST_URL, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == "00000":
                categories = result["data"].get("content", [])
                return categories
            else:
                return []
        except Exception as e:
            return []

    def get_subcategory_details(self, category_id):
        """
        第三步：根据大类ID获取小类问题详情
        参数：
            category_id: 大类ID（如29）
        返回：小类列表（失败返回空列表）
        """
        params = {
            "categoryId": category_id,
            "page": 0,
            "size": 9999  # 设为足够大的值，确保获取所有小类
        }
        try:
            headers = {**self.HEADERS, 'token': self.token}
            response = requests.get(self.SUBCATEGORY_LIST_URL, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == "00000":
                subcategories = result["data"].get("content", [])
                return subcategories
            else:
                return []
        except Exception as e:
            return []

    def calculate_subcategory_stats(self, subcategories):
        """
        统计小类的resolvedQty和unresolvedQty总和
        注意：需要处理主小类和sonIssuesList中的嵌套小类
        返回：统计结果字典 {"resolved_total": 数值, "unresolved_total": 数值}
        """
        resolved_total = 0
        unresolved_total = 0

        # 遍历每个小类
        for idx, sub in enumerate(subcategories):
            sub_id = sub.get("id")
            sub_title = sub.get("innerTitle", "未知标题")

            # 1. 主小类的数值（处理None/空值）
            sub_resolved = sub.get("resolvedQty")
            sub_unresolved = sub.get("unresolvedQty")
            # 转换None为0
            sub_resolved = 0 if sub_resolved is None else sub_resolved
            sub_unresolved = 0 if sub_unresolved is None else sub_unresolved

            resolved_total += sub_resolved
            unresolved_total += sub_unresolved

            # 2. 嵌套sonIssuesList中的小类数值
            son_issues = sub.get("sonIssuesList", [])
            for son_idx, son in enumerate(son_issues):
                son_id = son.get("id")
                son_title = son.get("innerTitle", "未知子标题")
                son_resolved = son.get("resolvedQty")
                son_unresolved = son.get("unresolvedQty")
                # 转换None为0
                son_resolved = 0 if son_resolved is None else son_resolved
                son_unresolved = 0 if son_unresolved is None else son_unresolved

                resolved_total += son_resolved
                unresolved_total += son_unresolved

        return {
            "resolved_total": resolved_total,
            "unresolved_total": unresolved_total
        }

    def print_final_stats(self, final_result):
        """
        格式化输出最终统计结果（重点：清晰展示每个大类的总计）
        """
        print("\n" + "=" * 80)
        print("📈 最终统计结果（按渠道+大类）")
        print("=" * 80)

        for date, channel_data in final_result.items():
            print(f"\n📅 统计日期：{date}")
            for channel_key, category_data in channel_data.items():
                print(f"\n  🔹 渠道：{channel_key}")
                if not category_data:
                    print(f"     └─ 无大类数据")
                    continue
                for category_id, stats in category_data.items():
                    print(f"     ├─ 大类ID：{category_id} | 大类名称：{stats['category_title']}")
                    print(f"     │  ├─ 已解决总数：{stats['resolved_total']}")
                    print(f"     │  └─ 未解决总数：{stats['unresolved_total']}")
        print("\n" + "=" * 80)

    def count_all(self):
        """主流程：整合所有步骤，统计并输出结果"""
        final_result = {}
        current_date = datetime.now().strftime("%Y-%m-%d")
        final_result[current_date] = {}

        # 第一步：获取渠道配置
        channels = self.get_channel_config()
        if not channels:
            return final_result

        # 遍历每个渠道（可先测试单个渠道，比如只测LOKLOK-APP）
        for channel in channels:
            app_name = channel.get("appName")
            client_group = channel.get("clientGroupCode")
            platform_type = channel.get("platformType")
            channel_key = f"{app_name}_{client_group}_{platform_type}"
            final_result[current_date][channel_key] = {}

            # 【可选】仅测试LOKLOK-APP渠道（减少请求量，方便调试）
            # if channel_key != "LOKLOK_LOKLOK_APP":
            #     continue

            # 第二步：获取大类
            categories = self.get_category_details(app_name, client_group, platform_type)
            if not categories:
                continue

            # 第三步：遍历大类，获取小类并统计
            for category in categories:
                category_id = category.get("id")
                # print(category_id)
                category_title = category.get("categoryTitle", "未知大类")

                # 获取小类
                subcategories = self.get_subcategory_details(category_id)
                # print(subcategories)
                if not subcategories:
                    final_result[current_date][channel_key][category_id] = {
                        "category_title": category_title,
                        "resolved_total": 0,
                        "unresolved_total": 0
                    }
                    continue

                # 统计小类数值
                stats = self.calculate_subcategory_stats(subcategories)

                # 保存结果
                final_result[current_date][channel_key][category_id] = {
                    "category_title": category_title,
                    "resolved_total": stats["resolved_total"],
                    "unresolved_total": stats["unresolved_total"]
                }

        # 格式化输出最终结果
        # self.print_final_stats(final_result)
        # 储存运行结果
        self.save_data_to_yaml_append(final_result)
        return final_result

    def save_data_to_yaml_append(self, data_dict: Dict, file_path: str = "data_save.yaml") -> None:
        """
        将统计数据字典追加保存到YAML文件，不覆盖任何历史数据：
        - 若文件中已存在当天数据 → 跳过写入（保留原有数据）
        - 若文件中无当天数据 → 新增该日期数据（持续写入）
        - 所有历史日期数据全程保留

        参数：
            data_dict: 待保存的字典（结构：{日期: {渠道: {大类ID: 统计数据}}}）
            file_path: 保存路径，默认当前目录下的data_save.yaml
        """
        # 1. 输入数据校验（保证数据格式合法）
        if not isinstance(data_dict, dict) or len(data_dict) == 0:
            raise ValueError("输入的data_dict必须是非空字典")

        # 提取新数据的日期键（假设data_dict仅包含一个日期的数据，符合业务逻辑）
        new_date_key = list(data_dict.keys())[0]
        if not isinstance(new_date_key, str) or len(new_date_key.split("-")) != 3:
            raise ValueError("data_dict的键必须是'YYYY-MM-DD'格式的日期字符串")

        try:
            # 2. 读取已有数据（若无文件则初始化为空字典）
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_data = yaml.load(f, Loader=yaml.FullLoader) or {}
            else:
                existing_data = {}

            # 3. 判断当天数据是否已存在 → 核心逻辑
            if new_date_key in existing_data:
                print(f"⚠️  日期[{new_date_key}]的数据已存在，跳过写入（不覆盖原有数据）")
                final_data = existing_data  # 保留原有数据，不做任何修改
            else:
                print(f"📝 日期[{new_date_key}]的数据不存在，新增写入")
                final_data = {**existing_data, **data_dict}  # 合并历史数据+新数据

            # 4. 写入YAML文件（保持格式美观，保留所有类型和中文）
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    final_data,
                    f,
                    allow_unicode=True,  # 支持中文显示
                    default_flow_style=False,  # 展开式格式（非压缩）
                    sort_keys=False,  # 保持键的原有顺序
                    indent=2  # 缩进2个空格，增强可读性
                )

            print(f"✅ 数据保存完成！")
            print(f"📂 文件路径：{os.path.abspath(file_path)}")
            print(f"📊 当前文件包含日期：{list(final_data.keys())}")

        except PermissionError:
            raise PermissionError(f"❌ 没有写入权限：{file_path}")
        except Exception as e:
            raise Exception(f"❌ 保存数据失败：{str(e)}")

    def load_yaml_data(self, file_path: str = "data_save.yaml") -> Dict:
        """
        读取YAML文件数据，处理文件不存在/空文件的情况
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ YAML文件不存在：{file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.load(f, Loader=yaml.FullLoader) or {}
            if not isinstance(data, dict):
                raise ValueError("❌ YAML文件数据格式错误，必须是字典类型")
            return data
        except Exception as e:
            raise Exception(f"❌ 读取YAML文件失败：{str(e)}")

    def get_yesterday_and_today_dates(self) -> Tuple[str, str]:
        """
        获取昨天和今天的日期字符串（格式：YYYY-MM-DD）
        """
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    def get_weekly_date_range(self) -> List[str]:
        """
        新增：获取过去7天的日期列表（按时间升序排列，含今天）
        返回格式：["2026-01-01", "2026-01-02", ..., "2026-01-07"]
        """
        today = datetime.now().date()
        # 生成过去7天日期（今天-6天 ~ 今天）
        weekly_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        return weekly_dates

    def compare_daily_data(self,
                           yaml_data: Dict,
                           yesterday_date: str,
                           today_date: str
                           ) -> Dict:
        """
        核心对比逻辑：计算每个大类的已解决/未解决数据变化（单日）
        返回格式：{渠道: {大类ID: {对比详情}}}
        """
        # 校验日期数据是否存在
        yesterday_data = yaml_data.get(yesterday_date, {})
        today_data = yaml_data.get(today_date, {})

        if not yesterday_data:
            print(f"⚠️  未找到[{yesterday_date}]的历史数据")
        if not today_data:
            print(f"⚠️  未找到[{today_date}]的今日数据")

        compare_result = {}

        # 遍历所有涉及的渠道（合并昨天和今天的渠道，避免遗漏）
        all_channels = set(yesterday_data.keys()).union(set(today_data.keys()))

        for channel in all_channels:
            compare_result[channel] = {}
            # 获取该渠道昨天和今天的大类数据
            yesterday_channel = yesterday_data.get(channel, {})
            today_channel = today_data.get(channel, {})

            # 遍历该渠道下所有涉及的大类（合并两天的大类）
            all_category_ids = set(yesterday_channel.keys()).union(set(today_channel.keys()))

            for category_id in all_category_ids:
                # 获取昨天的数值（无则为0）
                y_cat = yesterday_channel.get(category_id, {})
                y_resolved = y_cat.get("resolved_total", 0)
                y_unresolved = y_cat.get("unresolved_total", 0)
                y_title = y_cat.get("category_title", "未知大类")

                # 获取今天的数值（无则为0）
                t_cat = today_channel.get(category_id, {})
                t_resolved = t_cat.get("resolved_total", 0)
                t_unresolved = t_cat.get("unresolved_total", 0)
                t_title = t_cat.get("category_title", y_title)  # 优先用今天的标题，无则用昨天的

                # 计算变化值（今天 - 昨天）
                resolved_diff = t_resolved - y_resolved
                unresolved_diff = t_unresolved - y_unresolved

                # 标记变化类型（增长/减少/无变化）
                resolved_trend = "↑" if resolved_diff > 0 else "↓" if resolved_diff < 0 else "─"
                unresolved_trend = "↑" if unresolved_diff > 0 else "↓" if unresolved_diff < 0 else "─"

                compare_result[channel][category_id] = {
                    "category_title": t_title,
                    "yesterday_resolved": y_resolved,
                    "today_resolved": t_resolved,
                    "resolved_diff": resolved_diff,
                    "resolved_trend": resolved_trend,
                    "yesterday_unresolved": y_unresolved,
                    "today_unresolved": t_unresolved,
                    "unresolved_diff": unresolved_diff,
                    "unresolved_trend": unresolved_trend
                }

        return compare_result

    def compare_weekly_data(self, yaml_data: Dict, weekly_dates: List[str]) -> Dict:
        """
        新增：一周数据对比核心逻辑
        参数：
            yaml_data: 读取的YAML完整数据
            weekly_dates: 过去7天日期列表（升序）
        返回：{渠道: {大类ID: {一周对比详情}}}
        """
        # 过滤掉YAML中不存在的日期，保留有效数据日期
        valid_dates = [date for date in weekly_dates if date in yaml_data]
        if len(valid_dates) < 2:
            raise ValueError(f"❌ 一周对比需要至少2天有效数据，当前仅找到{len(valid_dates)}天")

        print(f"🔍 一周对比有效日期：{valid_dates[0]} ~ {valid_dates[-1]}（共{len(valid_dates)}天）")

        compare_result = {}
        # 1. 收集所有涉及的渠道和大类，整理每天的原始数据
        date_data_map = {}  # {日期: {渠道: {大类ID: {resolved, unresolved, title}}}}
        all_channels = set()
        all_category_ids = set()

        for date in valid_dates:
            date_data = yaml_data.get(date, {})
            date_data_map[date] = {}
            for channel, cat_data in date_data.items():
                all_channels.add(channel)
                date_data_map[date][channel] = {}
                for cat_id, cat_info in cat_data.items():
                    all_category_ids.add(cat_id)
                    date_data_map[date][channel][cat_id] = {
                        "resolved": cat_info.get("resolved_total", 0),
                        "unresolved": cat_info.get("unresolved_total", 0),
                        "title": cat_info.get("category_title", "未知大类")
                    }

        # 2. 逐渠道、逐大类计算一周变化指标
        for channel in all_channels:
            compare_result[channel] = {}
            for cat_id in all_category_ids:
                # 收集该大类每天的数值
                daily_resolved = []
                daily_unresolved = []
                cat_title = "未知大类"

                for date in valid_dates:
                    channel_data = date_data_map[date].get(channel, {})
                    cat_data = channel_data.get(cat_id, {})
                    daily_resolved.append(cat_data.get("resolved", 0))
                    daily_unresolved.append(cat_data.get("unresolved", 0))
                    # 优先取有值的标题
                    if cat_data.get("title") != "未知大类":
                        cat_title = cat_data["title"]

                # 计算核心指标
                first_resolved = daily_resolved[0]
                last_resolved = daily_resolved[-1]
                total_resolved_diff = last_resolved - first_resolved  # 累计变化
                avg_resolved_diff = round(total_resolved_diff / len(valid_dates), 2)  # 日均变化

                first_unresolved = daily_unresolved[0]
                last_unresolved = daily_unresolved[-1]
                total_unresolved_diff = last_unresolved - first_unresolved
                avg_unresolved_diff = round(total_unresolved_diff / len(valid_dates), 2)

                # 趋势标识
                resolved_trend = "↑" if total_resolved_diff > 0 else "↓" if total_resolved_diff < 0 else "─"
                unresolved_trend = "↑" if total_unresolved_diff > 0 else "↓" if total_unresolved_diff < 0 else "─"

                compare_result[channel][cat_id] = {
                    "category_title": cat_title,
                    "valid_dates": valid_dates,
                    "daily_resolved": daily_resolved,
                    "daily_unresolved": daily_unresolved,
                    "first_resolved": first_resolved,
                    "last_resolved": last_resolved,
                    "total_resolved_diff": total_resolved_diff,
                    "avg_resolved_diff": avg_resolved_diff,
                    "resolved_trend": resolved_trend,
                    "first_unresolved": first_unresolved,
                    "last_unresolved": last_unresolved,
                    "total_unresolved_diff": total_unresolved_diff,
                    "avg_unresolved_diff": avg_unresolved_diff,
                    "unresolved_trend": unresolved_trend
                }

        return compare_result

    def print_compare_result(self,
                             compare_result: Dict,
                             yesterday_date: str,
                             today_date: str) -> str:
        """
        改造后：返回单日对比结果的格式化字符串（用于飞书发送）
        返回：拼接好的统计字符串，兼容飞书消息换行/格式
        """
        # 初始化结果字符串
        result_str = ""

        # 拼接标题和分隔线
        result_str += "\n" + "=" * 120 + "\n"
        result_str += f"📊 数据变化对比 ({yesterday_date} → {today_date})" + "\n"
        result_str += "=" * 120 + "\n"

        for channel, category_data in compare_result.items():
            if not category_data:  # 渠道下无大类数据，跳过
                continue

            # 拼接渠道名称和分隔线
            result_str += f"\n🔹 渠道：{channel}" + "\n"
            result_str += "-" * 100 + "\n"

            # 拼接表头
            header_line = (
                f"{'大类ID':<8} {'大类名称':<20} {'已解决(昨日)':<12} {'已解决(今日)':<12} "
                f"{'已解决变化':<15} {'未解决(昨日)':<12} {'未解决(今日)':<12} {'未解决变化':<15}"
            )
            result_str += header_line + "\n"

            # 拼接表头分隔线
            separator_line = (
                f"{'─' * 8:<8} {'─' * 20:<20} {'─' * 12:<12} {'─' * 12:<12} "
                f"{'─' * 15:<15} {'─' * 12:<12} {'─' * 12:<12} {'─' * 15:<15}"
            )
            result_str += separator_line + "\n"

            # 拼接每个大类的统计数据
            for cat_id, stats in category_data.items():
                # 格式化变化值（带符号和趋势）
                resolved_diff_str = f"{stats['resolved_trend']} {stats['resolved_diff']:+}" if stats[
                                                                                                   'resolved_diff'] != 0 else "─ 0"
                unresolved_diff_str = f"{stats['unresolved_trend']} {stats['unresolved_diff']:+}" if stats[
                                                                                                         'unresolved_diff'] != 0 else "─ 0"

                # 拼接单行数据
                data_line = (
                    f"{cat_id:<8} "
                    f"{stats['category_title']:<20} "
                    f"{stats['yesterday_resolved']:<12} "
                    f"{stats['today_resolved']:<12} "
                    f"{resolved_diff_str:<15} "
                    f"{stats['yesterday_unresolved']:<12} "
                    f"{stats['today_unresolved']:<12} "
                    f"{unresolved_diff_str:<15}"
                )
                result_str += data_line + "\n"

        # 返回最终拼接的字符串
        return result_str

    def print_weekly_result(self, compare_result: Dict, weekly_dates: List[str]) -> str:
        """
        改造后：返回一周对比结果的格式化字符串（用于飞书发送）
        返回：拼接好的统计字符串，兼容飞书消息换行/格式
        """
        # 初始化结果字符串
        result_str = ""

        # 提取有效日期（从第一个有数据的大类中获取）
        valid_dates = []
        for channel_data in compare_result.values():
            for cat_stats in channel_data.values():
                valid_dates = cat_stats.get("valid_dates", [])
                break
            if valid_dates:
                break

        # 拼接一周对比标题和分隔线
        result_str += "\n" + "=" * 150 + "\n"
        result_str += f"📊 一周数据变化对比：{valid_dates[0]} ~ {valid_dates[-1]}（共{len(valid_dates)}天）" + "\n"
        result_str += "=" * 150 + "\n"

        for channel, category_data in compare_result.items():
            if not category_data:  # 渠道下无大类数据，跳过
                continue

            # 拼接渠道名称和分隔线
            result_str += f"\n🔹 渠道：{channel}" + "\n"
            result_str += "-" * 130 + "\n"

            # 构建日期表头（简化显示为MM-DD）
            date_header_resolved = " | ".join([f"{date[5:]}已解决" for date in valid_dates]) + " | "
            date_header_unresolved = " | ".join([f"{date[5:]}未解决" for date in valid_dates]) + " | "
            full_header = date_header_resolved + date_header_unresolved

            # 拼接表头
            header_line = (
                f"{'大类ID':<8} {'大类名称':<20} {full_header} "
                f"{'累计变化(已解决)':<15} {'日均变化(已解决)':<15} "
                f"{'累计变化(未解决)':<15} {'日均变化(未解决)':<15}"
            )
            result_str += header_line + "\n"

            # 拼接表头分隔线
            separator_line = (
                f"{'─' * 8:<8} {'─' * 20:<20} {'─' * (len(full_header) - 1):<{len(full_header) - 1}} "
                f"{'─' * 15:<15} {'─' * 15:<15} {'─' * 15:<15} {'─' * 15:<15}"
            )
            result_str += separator_line + "\n"

            # 拼接每个大类的一周数据
            for cat_id, stats in category_data.items():
                # 构建每天的数值字符串
                daily_resolved_str = " | ".join([f"{val:<8}" for val in stats['daily_resolved']]) + " | "
                daily_unresolved_str = " | ".join([f"{val:<8}" for val in stats['daily_unresolved']]) + " | "
                daily_str = daily_resolved_str + daily_unresolved_str

                # 格式化变化值
                total_resolved_str = f"{stats['resolved_trend']} {stats['total_resolved_diff']:+}" if stats[
                                                                                                          'total_resolved_diff'] != 0 else "─ 0"
                total_unresolved_str = f"{stats['unresolved_trend']} {stats['total_unresolved_diff']:+}" if stats[
                                                                                                                'total_unresolved_diff'] != 0 else "─ 0"

                # 拼接单行数据
                data_line = (
                    f"{cat_id:<8} "
                    f"{stats['category_title']:<20} "
                    f"{daily_str:<{len(full_header) - 1}} "
                    f"{total_resolved_str:<15} "
                    f"{stats['avg_resolved_diff']:<15} "
                    f"{total_unresolved_str:<15} "
                    f"{stats['avg_unresolved_diff']:<15}"
                )
                result_str += data_line + "\n"

        # 返回最终拼接的字符串
        return result_str

    def one_day_compare(self) -> None:
        """
        单日对比主方法：昨日vs今日
        """
        try:
            # 1. 读取YAML数据
            yaml_data = self.load_yaml_data("data_save.yaml")

            # 2. 获取昨天和今天的日期
            yesterday_date, today_date = self.get_yesterday_and_today_dates()
            title =f"🔍 待对比日期：昨天[{yesterday_date}] → 今天[{today_date}]"

            # 3. 执行数据对比
            compare_result = self.compare_daily_data(yaml_data, yesterday_date, today_date)

            # 4. 格式化输出结果
            content =self.print_compare_result(compare_result, yesterday_date, today_date)
            self.send_to_feishu(data=content, platform="Android",type="day_count", title=title)

        except FileNotFoundError as e:
            print(e)
            print("💡 提示：请先确保data_save.yaml文件存在，且包含至少两天的统计数据")
        except Exception as e:
            print(f"❌ 对比失败：{str(e)}")

    def weekly_compare(self) -> None:
        """
        新增：一周对比主方法
        """
        try:
            # 1. 读取YAML数据
            yaml_data = self.load_yaml_data("data_save.yaml")

            # 2. 获取过去7天日期范围
            weekly_dates = self.get_weekly_date_range()
            title= f"🔍 一周对比日期范围：{weekly_dates[0]} ~ {weekly_dates[-1]}"

            # 3. 执行一周数据对比
            compare_result = self.compare_weekly_data(yaml_data, weekly_dates)

            # 4. 格式化输出一周对比结果
            content = self.print_weekly_result(compare_result, weekly_dates)

            self.send_to_feishu(data=content, platform="Android",type="week_count", title=title)

        except FileNotFoundError as e:
            print(e)
            print("💡 提示：请先确保data_save.yaml文件存在，且包含至少两天的统计数据")
        except ValueError as e:
            print(e)
        except Exception as e:
            print(f"❌ 一周对比失败：{str(e)}")

    def run(self):
        """主运行逻辑"""
        try:
            print("🚀 反馈统计系统启动")
            current_hour = datetime.now().hour
            weekday = datetime.now().weekday()

            # 检查必要的配置
            if not self.token:
                print("❌ CMS登录失败，系统无法正常运行")
                return

            if not self.feedback_list:
                print("⚠️  未获取到反馈类型配置，可能影响统计功能")

            # 早上10点发送日报
            if current_hour == 10:
                self.count_all()
                # self.get_recent_feedback(hours=1)
                # self.get_daily_summary()
                self.one_day_compare()
                # 周一发送周报
                if weekday == 0:
                    self.get_recent_feedback(hours=1)
                    self.get_weekly_summary()
                    self.weekly_compare()
                else:
                    self.get_recent_feedback(hours=1)

            # 早上8点发送汇总明细
            elif current_hour == 8:
                self.get_recent_feedback(hours=8)

            else:
                self.get_recent_feedback(hours=1)

        except Exception as e:
            print(f"❌ 程序执行出错: {str(e)}")
            # 发送错误通知到飞书
            error_msg = f"反馈统计程序出错:\n**错误信息**: {str(e)}"
            self.send_to_feishu(error_msg, 'Android',
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


def main():
    """主函数"""
    print("=" * 60)
    print("欢迎使用 Loklok 反馈统计系统")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        # 创建统计实例
        feedback_count = FeedbackCount()

        # 显示帮助信息
        print("\n请选择操作:")
        print("1. 获取最近1小时反馈")
        print("2. 获取最近24小时反馈")
        print("3. 生成周汇总报告")
        print("4. 启动定时任务（后台运行）")
        print("5. 退出")

        choice = input("\n请输入选项 (1-5): ")

        if choice == '1':
            feedback_count.get_recent_feedback(hours=1)
        elif choice == '2':
            feedback_count.get_recent_feedback(hours=24)
        elif choice == '3':
            feedback_count.get_weekly_summary()
        elif choice == '4':
            print("⏳ 启动定时任务...")
            feedback_count.start()
            print("✅ 定时任务已启动，按 Ctrl+C 退出")
            feedback_count.join()
        elif choice == '5':
            print("👋 退出系统")
            sys.exit(0)
        else:
            print("❌ 无效选项，请重新选择")

    except KeyboardInterrupt:
        print("\n👋 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {str(e)}")


if __name__ == '__main__':
    count = FeedbackCount()
    count.run()
    # # 测试1：单日对比（昨日vs今日）
    # print("======= 单日对比 =======")
    # count.one_day_compare()

    # # 测试2：一周对比
    # print("\n======= 一周对比 =======")
    # count.weekly_compare()
