import requests
import json

def sendXZ(url,msg):

    # 你的数据内容
    data = {
        "msgtype": "text",
        "text": {
            "content": ""+msg+""
        }
    }

    # 假设你要发送到的URL是 'https://your-api-endpoint.com'
    #url = '机器人地址'

    # 将字典转换为JSON格式的字符串
    json_data = json.dumps(data)

    # 发送POST请求
    response = requests.post(url, data=json_data, headers={'Content-Type': 'application/json'})

    # 检查响应状态码
    if response.status_code == 200:
        print("请求成功！")
        # 处理响应内容
        response_data = response.json()
        print(response_data)
    else:
        print("请求失败，状态码：", response.status_code)
