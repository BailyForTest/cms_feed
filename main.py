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
import hashlib
import json
import threading
import requests
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor


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
        'iOS': 'https://open.feishu.cn/open-apis/bot/v2/hook/3b0f5a23-d5cd-45a4-9f53-033f1d62a351'
        # 'iOS': 'https://open.feishu.cn/open-apis/bot/v2/hook/f6b2fd6a-5bd1-4fea-be82-5ef644e7fe5e'
    }

    # API配置
    FEEDBACK_TAB_CONFIG_URL = "https://admin-api.netpop.app/user/behavior/backend/feedback/tab/config"
    FEEDBACK_LIST_URL = "https://admin-api.netpop.app/cms/backend/issues/type/list"
    CMS_LOGIN_URL = "https://admin-api.netpop.app/auth/backend/account/login"
    FEEDBACK_URL = 'https://admin-api.netpop.app/user/behavior/backend/feedback/v2/page/0'
    TRANSLATE_URL = "https://admin-api.netpop.app/third/backend/openai/translate"

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

    def get_feedback_value_from_json_str(self, json_str: str) -> str:
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
                if item.get("title") == "问题描述"  # 无 title 键 → 不匹配
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

    def send_to_feishu(self, data, platform, start_time, end_time):
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
            time_range = f"{start_time} 至 {end_time}"
            title = f"用户反馈 ({time_range})"

            # 使用飞书markdown格式
            markdown_content = f"### {title}\n\n{data}"

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

    def get_weekly_summary(self):
        """获取周汇总数据（优化版，只统计数量）"""
        try:
            print("⏳ 开始生成周汇总报告...")

            if not self.feedback_list:
                print("❌ 未获取到反馈类型列表，无法生成周汇总报告")
                return

            # 本周数据范围
            this_week_start, this_week_end = self.get_time_range(days=7)

            # 上周数据范围
            last_week_start = (self.now - timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S')
            last_week_end = (self.now - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S')

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

            # 构建汇总消息
            for key, data in summary_data.items():
                # 检查本周和上周的总反馈数，如果都为0则跳过
                if data['this_week']['total'] == 0 and data['last_week']['total'] == 0:
                    # print(f"⚠️  {data['appName']} - {data['clientGroup']} 本周和上周均无反馈数据，跳过发送")
                    continue

                # 构建消息内容
                content = f"**应用名称**: {data['appName']}\n"
                content += f"**渠道组**: {data['clientGroup']}\n\n"

                content += "**本周统计**:\n"
                content += f"- **总反馈数**: {data['this_week']['total']}\n"
                for type_name, count in data['this_week']['types'].items():
                    if count > 0:
                        content += f"  - **{type_name}**: {count}条\n"

                content += "\n**上周统计**:\n"
                content += f"- **总反馈数**: {data['last_week']['total']}\n"
                for type_name, count in data['last_week']['types'].items():
                    if count > 0:
                        content += f"  - **{type_name}**: {count}条\n"

                # 计算环比变化
                if data['last_week']['total'] > 0:
                    change_rate = ((data['this_week']['total'] - data['last_week']['total']) /
                                   data['last_week']['total'] * 100)
                    change_str = f"+{change_rate:.1f}%" if change_rate > 0 else f"{change_rate:.1f}%"
                    content += f"\n**环比变化**: {change_str}\n"
                elif data['this_week']['total'] > 0:
                    content += f"\n**环比变化**: 上周无数据，本周新增 {data['this_week']['total']} 条反馈\n"

                # 发送消息
                platform = 'iOS' if 'iOS' in data['appName'] or 'ios' in data['appName'] else 'Android'
                self.send_to_feishu(content, platform, this_week_start, this_week_end)
                valid_data_count += 1

            if valid_data_count == 0:
                print("✅ 本周和上周均无反馈数据，未发送任何周汇总报告")
            else:
                print(f"✅ 周汇总报告生成完成，共发送 {valid_data_count} 条报告")

        except Exception as e:
            print(f"❌ 生成周汇总报告失败: {str(e)}")

    def run(self):
        """主运行逻辑"""
        try:
            print("🚀 反馈统计系统启动")

            # 检查必要的配置
            if not self.token:
                print("❌ CMS登录失败，系统无法正常运行")
                return

            if not self.feedback_list:
                print("⚠️  未获取到反馈类型配置，可能影响统计功能")

            # 周四下午3点发送周报
            if datetime.now().weekday() == 3 and datetime.now().hour == 15:
                self.get_weekly_summary()

            current_hour = datetime.now().hour
            # 9-23点每小时运行
            if 8 < current_hour <= 23:
                self.get_recent_feedback(hours=1)
            # 早上8点发送汇总
            elif current_hour == 8:
                self.get_recent_feedback(hours=8)

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
