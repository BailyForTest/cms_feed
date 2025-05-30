#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# @Project : cms_feed
# @Time    : 2025/5/15 17:03
# @Author  : bj
# @Email   : 475829130@qq.com
# @File    : test.py
# @Software: PyCharm
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import time
import requests


# 获取当前的 UTC 时间戳
current_timestamp = time.time()
# 计算半个小时前的时间戳（减去 30 分钟，即 1800 秒）
half_hour_ago_timestamp = current_timestamp - 1*3600
# 将时间戳转换为 UTC 时间元组
current_time = time.gmtime(current_timestamp)
half_hour_ago = time.gmtime(half_hour_ago_timestamp)
# 格式化为指定的时间字符串格式
formatted_current_time = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', current_time)
formatted_half_hour_ago_time = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', half_hour_ago)
print(formatted_half_hour_ago_time)

mapping_dict = {
    "name": "姓名/公司名称",
    "roleTitle": "职位/角色",
    "copyrightHolder": "版权方名称",
    "country": "国家",
    "email": "邮箱",
    "mobile": "手机号",
    "address": "地址",
    "copyrightWorksTitle": "版权作品标题",
    "copyrightWorksDesc": "版权作品描述",
    "copyrightWorksUrl": "版权作品url",
    "copyrightWorksRegister": "版权登记号",
    "copyrightSupportingDocuments": "版权证明文件",
    "infringementRights": "侵权内容url",
    "infringementImgUrl": "侵权内容截图",
    "infringementDesc": "侵权内容描述",
    "status": "状态",
    "ipAddress": "IP地址",
    "region": "ip所属地区",
    "operatorId": "操作人",
    "operatorName": "操作人名称",
    "appName": "英语名",
    "createTime": "创建时间",
    "updateTime": "修改时间"
}


def get_website_feedback():
    url = "https://web-api.netpop.app/user/behavior/backend/website/feedback/page"
    payload = {
        "page": 0,
        "size": 10,
        # "startTime":  "2025-05-28T00:00:00.000Z"
        "startTime": formatted_half_hour_ago_time
    }
    headers = {
        "token": "",
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
        "Content-Type": "application/json",
        "content-type": "application/json"
    }
    response = requests.request("POST", url, json=payload, headers=headers)
    return response.json()


def replace_dict_keys(original_dict):
    result = {}
    for key, value in original_dict.items():
        # 如果当前键在映射字典中，则使用映射后的新键名
        # 否则保持原键名不变
        new_key = mapping_dict.get(key, key)
        result[new_key] = value
    return result


def webhook(url, data):
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
                                    "content": f"{formatted_half_hour_ago_time}-{formatted_current_time}时间内反馈如下：",
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


if __name__ == '__main__':
    url = "https://open.feishu.cn/open-apis/bot/v2/hook/701808df-64af-482d-a211-1b6344820642"
    feedback = get_website_feedback()
    text = ""
    if not feedback.get('data').get('content'):
        text = "可喜可贺！没有投诉哦，又渡过了平安的0.5h!"
        print(text)
        # webhook(url, text)
    else:
        for content in feedback.get('data').get('content'):
            text = str(replace_dict_keys(content)) + " \n"
            print(text)
            webhook(url, text)
