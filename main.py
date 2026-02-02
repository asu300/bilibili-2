import os
import json
import requests

FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
BILI_UIDS = [uid.strip() for uid in os.getenv("BILI_UIDS", "").split(",") if uid.strip()]
LAST_IDS_FILE = "last_ids.json"

# 加载历史记录
if os.path.exists(LAST_IDS_FILE):
    with open(LAST_IDS_FILE, "r") as f:
        last_ids = json.load(f)
else:
    last_ids = {}

new_last_ids = {}
has_new = False

for uid in BILI_UIDS:
    try:
        url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        if data["code"] != 0:
            print(f"⚠️ UID {uid} 返回错误码: {data['code']}")
            continue
        items = data["data"]["items"]
        if not items:
            continue
        latest = items[0]
        dynamic_id = latest["id_str"]
        old_id = last_ids.get(uid, "")
        if dynamic_id != old_id:
            has_new = True
            author = latest["modules"]["module_author"]["name"]
            desc = latest["modules"]["module_dynamic"].get("desc")
            content = desc["text"][:100] + "..." if desc and desc.get("text") else "无内容"
            
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
            if FEISHU_WEBHOOK:
                requests.post(FEISHU_WEBHOOK, json=msg)
                print(f"✅ 已推送 {author} 的新动态")
            else:
                print("❌ 未设置 FEISHU_WEBHOOK")
        new_last_ids[uid] = dynamic_id
    except Exception as e:
        print(f"❌ 获取 UID {uid} 动态失败: {e}")

# 保存最新 ID
with open(LAST_IDS_FILE, "w") as f:
    json.dump(new_last_ids, f, indent=2)

print("📭 检查完成" + ("，发现新动态！" if has_new else "，无新动态。"))
