import datetime
import json
import math
import random
import re
import time
import config
import notice
from encrypt import Encrypt
import requests
import hashlib
import logging
import pytz

AES_KEY = 'qbhajinldepmucsonaaaccgypwuvcjaa'
AES_IV = '2018534749963515'
SALT = '2af72f100c356273d46284f6fd1dfc08'

# AMAP_KEY = '9449339b6c4aee04d69481e6e6c84a84'

current_time = str(int(time.time() * 1000))
headers = {}
mt_version = "".join(re.findall('latest__version">(.*?)</p>',
                                requests.get('https://apps.apple.com/cn/app/i%E8%8C%85%E5%8F%B0/id1600482450').text,
                                re.S)).split(" ")[1]

header_context = f'''
MT-Lat: 28.499562
MT-K: 1675213490331
MT-Lng: 102.182324
Host: app.moutai519.com.cn
MT-User-Tag: 0
Accept: */*
MT-Network-Type: WIFI
MT-Token: 1
MT-Team-ID: 
MT-Info: 028e7f96f6369cafe1d105579c5b9377
MT-Device-ID: 2F2075D0-B66C-4287-A903-DBFF6358342A
MT-Bundle-ID: com.moutai.mall
Accept-Language: en-CN;q=1, zh-Hans-CN;q=0.9
MT-Request-ID: 167560018873318465
MT-APP-Version: 1.3.7
User-Agent: iOS;16.3;Apple;?unrecognized?
MT-R: clips_OlU6TmFRag5rCXwbNAQ/Tz1SKlN8THcecBp/HGhHdw==
Content-Length: 93
Accept-Encoding: gzip, deflate, br
Connection: keep-alive
Content-Type: application/json
userId: 2
'''


def init_headers(user_id: str = '1', token: str = '2', lat: str = '28.499562', lng: str = '102.182324'):
    for k in header_context.rstrip().lstrip().split("\n"):
        temp_l = k.split(': ')
        dict.update(headers, {temp_l[0]: temp_l[1]})
    dict.update(headers, {"userId": user_id})
    dict.update(headers, {"MT-Token": token})
    dict.update(headers, {"MT-Lat": lat})
    dict.update(headers, {"MT-Lng": lng})
    dict.update(headers, {"MT-APP-Version": mt_version})


def signature(data: dict):
    keys = sorted(data.keys())
    temp_v = ''
    for item in keys:
        temp_v += data[item]
    text = SALT + temp_v + current_time
    hl = hashlib.md5()
    hl.update(text.encode(encoding='utf8'))
    md5 = hl.hexdigest()
    return md5


print()


def get_vcode(mobile: str):
    params = {'mobile': mobile}
    md5 = signature(params)
    dict.update(params, {'md5': md5, "timestamp": current_time, 'MT-APP-Version': mt_version})
    responses = requests.post("https://app.moutai519.com.cn/xhr/front/user/register/vcode", json=params,
                              headers=headers)

    logging.info(
        f'get v_code : params : {params}, response code : {responses.status_code}, response body : {responses.text}')


def login(mobile: str, v_code: str):
    params = {'mobile': mobile, 'vCode': v_code, 'ydToken': '', 'ydLogId': ''}
    md5 = signature(params)
    dict.update(params, {'md5': md5, "timestamp": current_time, 'MT-APP-Version': mt_version})
    responses = requests.post("https://app.moutai519.com.cn/xhr/front/user/register/login", json=params,
                              headers=headers)
    if responses.status_code != 200:
        logging.info(
            f'login : params : {params}, response code : {responses.status_code}, response body : {responses.text}')
    dict.update(headers, {'MT-Token': responses.json()['data']['token']})
    dict.update(headers, {'userId': responses.json()['data']['userId']})
    return responses.json()['data']['token'], responses.json()['data']['userId']


def get_current_session_id():
    day_time = get_day_time()
    responses = requests.get(f"https://static.moutai519.com.cn/mt-backend/xhr/front/mall/index/session/get/{day_time}")
    if responses.status_code != 200:
        logging.warning(
            f'get_current_session_id : params : {day_time}, response code : {responses.status_code}, response body : {responses.text}')
    current_session_id = responses.json()['data']['sessionId']
    dict.update(headers, {'current_session_id': str(current_session_id)})


def get_day_time():

    # 创建一个东八区（北京时间）的时区对象
    beijing_tz = pytz.timezone('Asia/Shanghai')

    # 获取当前北京时间的日期和时间对象
    beijing_dt = datetime.datetime.now(beijing_tz)

    # 设置时间为0点
    beijing_dt = beijing_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    # 获取时间戳（以秒为单位）
    timestamp = int(beijing_dt.timestamp()) * 1000
    return timestamp


def get_location_count(province: str,
                       city: str,
                       item_code: str,
                       p_c_map: dict,
                       source_data: dict,
                       lat: str ,
                       lng: str):
    day_time = get_day_time()
    session_id = headers['current_session_id']
    responses = requests.get(
        f"https://static.moutai519.com.cn/mt-backend/xhr/front/mall/shop/list/slim/v3/{session_id}/{province}/{item_code}/{day_time}")
    if responses.status_code != 200:
        logging.warning(
            f'get_location_count : params : {day_time}, response code : {responses.status_code}, response body : {responses.text}')
    shops = responses.json()['data']['shops']
    logging.info(f"shops : {shops}")
    if config.MAX_ENABLED:
        return max_shop(city, item_code, p_c_map, province, shops)
    if config.DISTANCE_ENABLED:
        return distance_shop(city, item_code, p_c_map, province, shops, source_data, lat, lng)


def distance_shop(city,
                  item_code,
                  p_c_map,
                  province,
                  shops,
                  source_data,
                  lat: str = '28.499562',
                  lng: str = '102.182324'):
    # shop_ids = p_c_map[province][city]
    temp_list = []
    for shop in shops:
        shopId = shop['shopId']
        items = shop['items']
        item_ids = [i['itemId'] for i in items]
        # if shopId not in shop_ids:
        #     continue
        if str(item_code) not in item_ids:
            continue
        shop_info = source_data.get(shopId)
        # d = geodesic((lat, lng), (shop_info['lat'], shop_info['lng'])).km
        d = math.sqrt((float(lat) - shop_info['lat']) ** 2 + (float(lng) - shop_info['lng']) ** 2)
        # print(f"距离：{d}")
        temp_list.append((d, shopId))

    # sorted(a,key=lambda x:x[0])
    temp_list = sorted(temp_list, key=lambda x: x[0])
    # logging.info(f"所有门店距离:{temp_list}")
    if len(temp_list) > 0:
        return temp_list[0][1]
    else:
        return '0'


def max_shop(city, item_code, p_c_map, province, shops):
    max_count = 0
    max_shop_id = '0'
    shop_ids = p_c_map[province][city]
    for shop in shops:
        shopId = shop['shopId']
        items = shop['items']

        if shopId not in shop_ids:
            continue
        for item in items:
            if item['itemId'] != str(item_code):
                continue
            if item['inventory'] > max_count:
                max_count = item['inventory']
                max_shop_id = shopId
    logging.debug(f'item code {item_code}, max shop id : {max_shop_id}, max count : {max_count}')
    return max_shop_id


encrypt = Encrypt(key=AES_KEY, iv=AES_IV)


def act_params(shop_id: str, item_id: str):
    # {
    #     "actParam": "a/v0XjWK/a/a+ZyaSlKKZViJHuh8tLw==",
    #     "itemInfoList": [
    #         {
    #             "count": 1,
    #             "itemId": "2478"
    #         }
    #     ],
    #     "shopId": "151510100019",
    #     "sessionId": 508
    # }
    session_id = headers['current_session_id']
    userId = headers['userId']
    params = {"itemInfoList": [{"count": 1, "itemId": item_id}],
              "sessionId": int(session_id),
              "userId": userId,
              "shopId": shop_id
              }
    s = json.dumps(params)
    act = encrypt.aes_encrypt(s)
    params.update({"actParam": act})
    return params

# 此方法修改为制定消息平台，并非发送邮件
def send_email(msg: str):
    logging.info("send msg to xz")
    if config.PUSH_TOKEN is None:
        return
    # title = 'imoutai预约失败'  # 改成你要的标题内容
    # content = msg  # 改成你要的正文内容
    # url = 'http://www.pushplus.plus/send'
    # r = requests.get(url, params={'token': config.PUSH_TOKEN,
    #                               'title': title,
    #                               'content': content})
    notice.sendXZ(config.PUSH_TOKEN,msg=msg)
    #logging.info(f'通知推送结果：{r.status_code, r.text}')


def reservation(params: dict, mobile: str):
    params.pop('userId')
    responses = requests.post("https://app.moutai519.com.cn/xhr/front/mall/reservation/add", json=params,
                              headers=headers)
    if responses.status_code == 401:
        send_email(f'[{mobile}],登录token失效，需要重新登录')
        raise RuntimeError
    if '您的实名信息未完善或未通过认证' in responses.text:
        send_email(f'[{mobile}],{responses.text}')
        raise RuntimeError
    logging.info(
        f'预约 : mobile:{mobile} :  response code : {responses.status_code}, response body : {responses.text}')
    send_email(f'[{mobile}],{responses.text}')




def select_geo(i: str):
    # https://www.piliang.tech/geocoding-amap
    resp = requests.get(f"https://www.piliang.tech/api/amap/geocode?address={i}")
    geocodes: list = resp.json()['geocodes']
    return geocodes


def get_map(lat: str = '28.499562', lng: str = '102.182324'):
    p_c_map = {}
    url = 'https://static.moutai519.com.cn/mt-backend/xhr/front/mall/resource/get'
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0_1 like Mac OS X)',
        'Referer': 'https://h5.moutai519.com.cn/gux/game/main?appConfig=2_1_2',
        'Client-User-Agent': 'iOS;16.0.1;Apple;iPhone 14 ProMax',
        'MT-R': 'clips_OlU6TmFRag5rCXwbNAQ/Tz1SKlN8THcecBp/HGhHdw==',
        'Origin': 'https://h5.moutai519.com.cn',
        'MT-APP-Version': mt_version,
        'MT-Request-ID': f'{int(time.time() * 1000)}{random.randint(1111111, 999999999)}{int(time.time() * 1000)}',
        'Accept-Language': 'zh-CN,zh-Hans;q=1',
        'MT-Device-ID': f'{int(time.time() * 1000)}{random.randint(1111111, 999999999)}{int(time.time() * 1000)}',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'mt-lng': f'{lng}',
        'mt-lat': f'{lat}'
    }
    res = requests.get(url, headers=headers, )
    mtshops = res.json().get('data', {}).get('mtshops_pc', {})
    urls = mtshops.get('url')
    r = requests.get(urls)
    for k, v in dict(r.json()).items():
        provinceName = v.get('provinceName')
        cityName = v.get('cityName')
        if not p_c_map.get(provinceName):
            p_c_map[provinceName] = {}
        if not p_c_map[provinceName].get(cityName, None):
            p_c_map[provinceName][cityName] = [k]
        else:
            p_c_map[provinceName][cityName].append(k)

    return p_c_map, dict(r.json())


def getUserEnergyAward(mobile: str):
    """
    领取耐力
    """
    cookies = {
        'MT-Device-ID-Wap': headers['MT-Device-ID'],
        'MT-Token-Wap': headers['MT-Token'],
        'YX_SUPPORT_WEBP': '1',
    }
    response = requests.post('https://h5.moutai519.com.cn/game/isolationPage/getUserEnergyAward', cookies=cookies,
                             headers=headers, json={})
    # response.json().get('message') if '无法领取奖励' in response.text else "领取奖励成功"
    logging.info(
        f'领取耐力 : mobile:{mobile} :  response code : {response.status_code}, response body : {response.text}')
