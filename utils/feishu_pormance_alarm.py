import sys
import requests
import json
import re
import datetime
import time


class FeishuApi():

    def __init__(self):
        self.tenant_access_token = self.get_tenant_access_token()
        self.headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': self.tenant_access_token
        }
        # 指定共享空间下的指定文件夹id
        self.folder_token = "fldcnHVxcxaDiPTBsnBl7ENq6b"
        # 自己的token
        self.open_id = "ou_64dee8b6xc452x424bfcf8eb11fc0e55"
        # 消息发送群聊
        self.send_chart_id = "oc_cf032ab2a14f6ax3z174fa01xx9a6bf0"
        # @人员ID
        self.send_user_id = "ou_29d1477cbDe6Ns0d7c3f9f89b82f2f94"

    # 获取小程序token
    def get_tenant_access_token(self):
        # 应用凭证：
        # 应用标识
        app_id = "cli_a3ddecDDsa391120d"
        # 标识密钥
        app_secret = "9POqHSAgtJuOLxcasd0mA6gQOksdAdUYc"
        req_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        post_param = {
            "app_id": app_id,
            "app_secret": app_secret
        }
        res = requests.post(req_url, json=post_param)
        if res.status_code == 200:
            res_json = res.json()
            tenant_access_token = res_json.get("tenant_access_token")
            return "Bearer {}".format(tenant_access_token)
        print("获取 性能监控一键统计小程序 应用token失败！！跳出程序")

    # 根据应用token，拿到所有添加了小程序的群聊
    def get_all_chart_id(self):
        req_url = "https://open.feishu.cn/open-apis/im/v1/chats"
        res = requests.get(req_url, headers=self.headers)
        if res.status_code == 200:
            res_json = res.json()
            data = res_json.get("data")
            item_group = data.get("items")
            # 循环返回结果，将 群聊名称、id组装成词典
            chart_id_map = {}
            for item in item_group:
                chart_id_map[item.get("name")] = item.get("chat_id")
            print("添加了小程序的群聊信息：", chart_id_map)
            return chart_id_map
        print("根据 应用token获取所有添加了小程序的群聊 失败！！！跳出程序")

    # 获取群聊中所有的历史报警信息
    def parse_alarm_info(self, page_token, chart_id, alarm_list, exec_time, today_start_time, today_end_time):
        req_url = "https://open.feishu.cn/open-apis/im/v1/messages"
        get_param = {}
        if page_token.strip() == '':
            if exec_time == '':
                get_param = {
                    "container_id": chart_id,
                    "container_id_type": "chat",
                    "page_size": 50,
                    "start_time": today_start_time,
                    "end_time": today_end_time
                }
            else:
                get_param = {
                    "container_id": chart_id,
                    "container_id_type": "chat",
                    "page_size": 50
                }
        else:
            if exec_time == '':
                get_param = {
                    "container_id": chart_id,
                    "container_id_type": "chat",
                    "page_size": 50,
                    "start_time": today_start_time,
                    "end_time": today_end_time,
                    "page_token": page_token
                }
            else:
                get_param = {
                    "container_id": chart_id,
                    "container_id_type": "chat",
                    "page_size": 50,
                    "page_token": page_token
                }
        res = requests.get(req_url, params=get_param, headers=self.headers)
        if res.status_code == 200:
            res_json = res.json()
            data = res_json.get("data")
            new_page_token = data.get("page_token")
            has_more = data.get("has_more")
            item_group = data.get("items")
            # 解析报错信息
            for item in item_group:
                # noinspection PyBroadException
                try:
                    # 判断 msg_type 是否为 text; sender.sender_type 是否是 app
                    msg_type = item.get("msg_type")
                    sender_type = item.get("sender").get("sender_type")
                    if msg_type != "text" or sender_type != "app":
                        continue
                    # 解析字符串， 组装Excel对象
                    error_msg = item.get("body").get("content")
                    error_text = json.loads(error_msg).get("text")
                    text_list = error_text.split('\n')
                    project_name = text_list[0].lstrip("【服务名称】: ")
                    error_time = text_list[1].lstrip("【异常时间】: ")
                    environment = text_list[2].lstrip("【环境】: ")
                    function_url = text_list[5].lstrip("【请求路径】:  ")
                    time_text = text_list[8].lstrip("【异常描述】: ")
                    # 拿到耗时和阈值
                    threshold_pattern = re.compile('阈值(.*?)ms', re.S)
                    threshold = threshold_pattern.findall(time_text)[0]
                    consuming_pattern = re.compile('耗时(.*?)ms', re.S)
                    consuming = consuming_pattern.findall(time_text)[0]
                    timeout = str(int(consuming) - int(threshold))
                    row_info = ExcelRowInfo(project_name, error_time, environment, function_url, consuming, timeout)
                    alarm_list.append(row_info)
                except Exception as e:
                    print("解析报错信息失败，判断为非性能监控报警，跳过")
                    continue
            if bool(has_more):
                # 递归调用
                self.parse_alarm_info(str(new_page_token), chart_id, alarm_list, exec_time, today_start_time, today_end_time)
        else:
            print("获取群聊中所有的历史报警信息 失败！！！跳出程序", get_param)

    # 发送消息给指定群聊
    def send_info_to_chart(self, text):
        # content = "{\"text\":\"" + str(text) + "<at user_id =\\\"" + self.send_user_id + "\\\">刘斌</at>" + "\"}"
        content = "{\"text\":\"" + str(text) + "\"}"
        req_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
        post_param = {
          "receive_id": self.send_chart_id,
          "msg_type": "text",
          "content": content
        }
        res = requests.post(req_url, json=post_param, headers=self.headers)
        if res.status_code == 200:
            print("发送文档地址到指定群聊成功")
        else:
            print("发送文档地址到指定群聊失败")
        print(content)


    # 指定目录下创建Excel文件
    def create_excel(self, excel_data):
        # 准备Excel文件名称
        excel_name = "性能监控报警信息" + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        # 创建Excel文件
        req_url = "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets"
        post_param = {
            "title": excel_name,
            "folder_token": self.folder_token
        }
        res = requests.post(req_url, json=post_param, headers=self.headers)
        if res.status_code == 200:
            res_json = res.json()
            spreadsheet = res_json.get("data").get("spreadsheet")
            print("创建Excel文件成功，文件地址：", spreadsheet.get("url"))
            # 将url发送到指定群聊
            self.send_info_to_chart(spreadsheet.get("url"))
            return spreadsheet.get("spreadsheet_token")
        else:
            print("创建Excel文件失败")

    # 将创建的Excel所有权转移给自己，目的是可以删除冗余文件
    def add_permissions(self, spreadsheet_token):
        req_url = "https://open.feishu.cn/open-apis/drive/v1/permissions/{}/members?need_notification=false&type=sheet".format(spreadsheet_token)
        post_param = {
            "member_id": self.open_id,
            "member_type": "openid",
            "perm": "full_access"
        }
        res = requests.post(req_url, json=post_param, headers=self.headers)
        if res.status_code == 200:
            print("添加用户权限成功")
        else:
            print("添加用户权限失败")

    # 将数据写到文件中
    def write_excel_info(self, spreadsheet_token, data):
        excel = ExcelWriterUtil(spreadsheet_token, data, self.tenant_access_token)
        # 第一步先获取excel第一页的sheet信息
        sheet_id = excel.get_sheet_info()
        # 循环数据，写入工作表
        index = 0
        for map_key, map_value in data.items():
            # 如果是第一页，使用第一页的id
            if index == 0:
                # 更改sheet页的名字
                excel.update_sheet_name(map_key, sheet_id)
            else:
                # 先添加一个sheet页
                sheet_id = excel.add_sheet(index, map_key)
            # 增加行，先准备好行数
            excel.add_empty_row(sheet_id, len(map_value) + 1)
            # 写入数据
            excel.write_data(sheet_id, map_value)
            index = index + 1


# 准备Excel行数据对象
class ExcelRowInfo():
    def __init__(self, project_name, error_time, environment, function_url, consuming, timeout):
        self.project_name = project_name
        self.error_time = error_time
        self.environment = environment
        self.function_url = function_url
        self.consuming = consuming
        self.timeout = timeout


# Excel工具类
class ExcelWriterUtil():
    def __init__(self, spreadsheet_token, data, tenant_access_token):
        self.spreadsheet_token = spreadsheet_token
        self.data = data
        self.tenant_access_token = tenant_access_token
        self.headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': self.tenant_access_token
        }

    # 获取excel的sheet信息
    def get_sheet_info(self):
        req_url = "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{}/sheets/query".format(self.spreadsheet_token)
        res = requests.get(req_url, headers=self.headers)
        if res.status_code == 200:
            res_json = res.json()
            sheet_info = res_json.get("data").get("sheets")[0]
            return sheet_info.get("sheet_id")
        else:
            print("获取excel的sheet信息失败")

    # 更改sheet页的名字
    def update_sheet_name(self, sheet_name, sheet_id):
        req_url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{}/sheets_batch_update".format(self.spreadsheet_token)
        post_param = {
            "requests": [
                {
                    "updateSheet": {
                        "properties": {
                            "sheetId": sheet_id,
                            "title": sheet_name
                        }
                    }
                }
            ]
        }
        res = requests.post(req_url, json=post_param, headers=self.headers)
        if res.status_code == 200:
            print("更改sheet页名称成功")
        else:
            print("更改sheet页名称失败")

    # 新增一个sheet页
    def add_sheet(self, index, sheet_name):
        req_url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{}/sheets_batch_update".format(self.spreadsheet_token)
        post_param = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": sheet_name,
                            "index": index
                        }
                    }
                }
            ]
        }
        res = requests.post(req_url, json=post_param, headers=self.headers)
        if res.status_code == 200:
            print("新增sheet页名称成功", sheet_name)
            # 返回sheet_id
            res_json = res.json()
            return res_json.get("data").get("replies")[0].get("addSheet").get("properties").get("sheetId")
        else:
            print("新增sheet页名称失败")

    # 添加行数
    def add_empty_row(self, sheet_id, add_row_length):
        req_url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{}/dimension_range".format(self.spreadsheet_token)
        row_length = 0
        loop_flag = True
        # 需要添加的行数有没有超过5000条，如果超过递归
        if add_row_length > 4000:
            add_row_length = add_row_length - 4000
            row_length = 4000
        else:
            row_length = add_row_length
            loop_flag = False
        post_param = {
            "dimension": {
                "sheetId": sheet_id,
                "majorDimension": "ROWS",
                "length": row_length
            }
        }
        res = requests.post(req_url, json=post_param, headers=self.headers)
        if res.status_code == 200:
            if bool(loop_flag):
                self.add_empty_row(sheet_id, add_row_length)
        else:
            print("添加空行失败")

    # 写入数据
    def write_data(self, sheet_id, row_data):
        all_row_info = [["项目信息", "报错时间", "环境", "接口url", "耗时(ms)", "超时(ms)", "处理状态", "处理人"]]
        # 先处理数据
        for data in row_data:
            row_info = []
            row_info.append(str(data.project_name))
            row_info.append(str(data.error_time))
            row_info.append(str(data.environment))
            row_info.append(str(data.function_url))
            row_info.append(str(data.consuming))
            row_info.append(str(data.timeout))
            row_info.append("未处理")
            row_info.append('')
            all_row_info.append(row_info)
        req_url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{}/values_prepend".format(self.spreadsheet_token)
        # 总数据条数
        count = len(all_row_info)
        limit = 4000
        for index in range(0, count, limit):
            range_info = sheet_id + "!A" + str(index + 1) + ":H" + str(index + 1 + limit)
            limit_row_info = all_row_info[index:index + limit]
            post_param = {
                "valueRange": {
                    "range": str(range_info),
                    "values": limit_row_info
                }
            }
            res = requests.post(req_url, json=post_param, headers=self.headers)
            if res.status_code == 200:
                print("从第", str(index + 1), "行插入数据成功")
            else:
                print("从第", str(index + 1), "行插入数据失败")


# 处理飞书性能监控群中的报警信息
if __name__ == '__main__':
    # 首先判断有没有入参，如果有入参则拉取全量数据，否则拉取当天数据
    exec_time = 'all'
    today_start_time = 0
    today_end_time = 0
    if len(sys.argv) < 2:
        exec_time = ''
        # 无入参，当天数据
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        # 今天开始时间戳
        today_start_time = int(time.mktime(time.strptime(str(today), '%Y-%m-%d')))
        # 今天结束时间戳
        today_end_time = int(time.mktime(time.strptime(str(tomorrow), '%Y-%m-%d'))) - 1
        # print(today_start_time)
        # print(today_end_time)
        # quit()
    else:
        if sys.argv[1] != "all":
            print("请检查脚本入参格式后重新输入:")
            print("python feishu_pormance_alarm.py all")
            quit()

    #第一步，获取token
    feishu = FeishuApi()
    # 拿到所有添加应用的群聊
    chart_id_map = feishu.get_all_chart_id()
    # 循环获取超时报警信息
    alarm_map = {}
    for map_key, map_value in chart_id_map.items():
        alarm_list = []
        feishu.parse_alarm_info('', map_value, alarm_list, exec_time, today_start_time, today_end_time)
        if alarm_list:
            alarm_map[map_key] = alarm_list
    # 先创建Excel
    spreadsheet_token = feishu.create_excel(alarm_map)
    # spreadsheet_token = "shtcsdasdP2aITMm0VCWTbV2Efc"
    # 将自己赋予文件管理权限
    feishu.add_permissions(spreadsheet_token)
    # 将数据写到文件中
    feishu.write_excel_info(spreadsheet_token, alarm_map)
    print("性能监控小程序运行完成！！！")