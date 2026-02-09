import requests
import json
import time
import logging
import threading
from bilibili_api import user, sync

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 飞书机器人 Webhook URL
webhook_url = '这里填你的飞书机器人 Webhook URL'
# 例如我的  'https://open.feishu.cn/open-apis/bot/v2/hook/4f06d2df-0682-4420-a5d2-xxxxxxxxx'

# 设置视频的 bvid
newbvid = ''  # 必须填写有效的 bvid

# 定义请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 目标用户名 可以填多个
target_usernames = ['洪洪火火复盘'] 

# 存储已输出的评论 ID
printed_rpids = set()

# 发送飞书消息
def send_feishu_message(content):
    try:
        message = {
            "msg_type": "text",
            "content": {"text": content}
        }
        response = requests.post(webhook_url, data=json.dumps(message), headers={'Content-Type': 'application/json'})
        if response.status_code != 200:
            logging.error(f"飞书消息发送失败，状态码：{response.status_code}")
    except Exception as e:
        logging.error(f"飞书消息发送异常: {e}")

# 获取并处理评论
def fetch_comments():
    global newbvid  # 声明使用全局变量
    if not newbvid:
        logging.warning("newbvid 未设置，请检查配置！")
        return

    url = f'https://api.bilibili.com/x/v2/reply/main?type=1&oid={newbvid}&mode=2'
    try:
        logging.info("开始获取评论数据...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data['code'] == 0:
            logging.info("成功获取评论数据")
            comments = data['data']['replies']
            top_replies = data['data']['top_replies']

            # 处理置顶评论
            if top_replies:
                for top_reply in top_replies:
                    rpid = top_reply['rpid']
                    if rpid not in printed_rpids:
                        logging.info(f"顶楼评论: {top_reply['content']['message']}")
                        send_feishu_message(f"用户: {top_reply['member']['uname']}\n置顶评论内容: {top_reply['content']['message']}")
                        printed_rpids.add(rpid)

            # 处理普通评论
            if comments:
                for comment in comments:
                    if comment['member']['uname'] in target_usernames:
                        rpid = comment['rpid']
                        if rpid not in printed_rpids:
                            logging.info(f"用户: {comment['member']['uname']}, 评论: {comment['content']['message']}")
                            send_feishu_message(f"用户: {comment['member']['uname']}\n评论内容: {comment['content']['message']}")
                            printed_rpids.add(rpid)
        else:
            logging.error(f"请求失败，错误代码：{data['code']}")
    except requests.exceptions.RequestException as e:
        logging.error(f"网络请求失败: {e}")
    except json.JSONDecodeError:
        logging.error("无法解析返回的 JSON 数据")
    except Exception as e:
        logging.error(f"未知错误: {e}")

# 实例化 UP 主对象
u = user.User(1671203508)

# 获取动态数据
async def main():
    global newbvid  # 使用全局变量
    offset = ""
    dynamics = []
    while True:
        page = await u.get_dynamics_new(offset)
        for item in page['items']:
            module_dynamic = item['modules']['module_dynamic']
            if module_dynamic and 'major' in module_dynamic:
                archive = module_dynamic['major'].get('archive', None)
                if archive:
                    bvid = archive.get('bvid', '没有 bvid')
                    title = archive.get('title', '没有标题')
                    aid = archive.get('aid', '没有 aid')
                    newbvid = bvid
                    logging.info(f"bvid: {newbvid}, title: {title}, aid: {aid}")
                    return  # 直接退出整个函数，不再处理后续动态
        dynamics.extend(page["items"])
        if page["has_more"] != 1:
            break
        offset = page["offset"]
    logging.info(f"共有 {len(dynamics)} 条动态")

# 定时运行 main()
def run_main_periodically():
    while True:
        sync(main())
        logging.info("等待一小时后再次运行 main()")
        time.sleep(3600)

# 定时运行 fetch_comments()
def run_fetch_comments_periodically():
    while True:
        fetch_comments()
        logging.info("等待 3 秒后再次运行 fetch_comments()")
        time.sleep(3)

# 启动两个独立线程
threading.Thread(target=run_main_periodically, daemon=True).start()
threading.Thread(target=run_fetch_comments_periodically, daemon=True).start()

# 主线程保持运行
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logging.info("程序退出")