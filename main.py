import os
import json
import requests
from datetime import datetime

# 配置
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
BILI_UIDS = os.getenv("BILI_UIDS", "").split(",")
LAST_IDS_FILE = "last_ids.json"

# 加载已记录的最新动态 ID
if os.path.exists(LAST_IDS_DIR):
    with open(LAST_IDS_FILE, "r") as f:
        last_ids = json.load(f)
else:
    last_ids = {}

new_last_ids = {}
has_new = False

for uid in BILI_UIDS:
    if not uid.strip():
        continue
    url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid.strip()}"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        if data["code"] != 0:
            continue
        items = data["data"]["items"]
        if not items:
            continue
        latest = items[0]
        dynamic_id = latest["id_str"]
        old_id = last_ids.get(uid, "")
        if dynamic_id != old_id:
            # 有新动态！
            has_new = True
            title = "【B站新动态】"
            content = "暂无内容"
            author = latest["modules"]["module_author"]["name"]
            
            # 提取内容
            if "module_dynamic" in latest and latest["modules"]["module_dynamic"]["desc"]:
                content = latest["modules"]["module_dynamic"]["desc"]["text"][:100] + "..."
            
            # 构造飞书消息
            msg = {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": f"{author} 发布了新动态",
                            "content": [
                                [{"tag": "text", "text": f"UP主: {author}\n"}],
                                [{"tag": "text", "text": f"内容: {content}\n"}],
                                [{"tag": "a", "text": "点击查看", "href": f"https://t.bilibili.com/{dynamic_id}"}]
                            ]
                        }
                    }
                }
            }
            # 发送到飞书
            requests.post(FEISHU_WEBHOOK, json=msg)
            print(f"✅ 已推送 {author} 的新动态")
        new_last_ids[uid] = dynamic_id
    except Exception as e:
        print(f"❌ 获取 {uid} 动态失败: {e}")

# 保存最新 ID
with open(LAST_IDS_FILE, "w") as f:
    json.dump(new_last_ids, f)

if not has_new:
    print("📭 未发现新动态")
