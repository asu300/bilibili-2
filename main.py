import os
import json
import requests
import time

FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
BILI_UIDS = [uid.strip() for uid in os.getenv("BILI_UIDS", "").split(",") if uid.strip() and uid.isdigit()]
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
    success = False
    for attempt in range(2):  # 重试1次
        try:
            url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": f"https://space.bilibili.com/{uid}/",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Origin": "https://space.bilibili.com"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            
            # 打印调试信息（可临时保留）
            print(f"🔍 UID {uid} | 状态码: {resp.status_code} | 响应长度: {len(resp.text)}")
            
            if resp.status_code == 200 and resp.text.strip():
                data = resp.json()
                if data["code"] == 0:
                    success = True
                    items = data["data"]["items"]
                    if items:
                        latest = items[0]
                        dynamic_id = latest["id_str"]
                        old_id = last_ids.get(uid, "")
                        if dynamic_id != old_id:
                            has_new = True
                            author = latest["modules"]["module_author"]["name"]
                            desc = latest["modules"]["module_dynamic"].get("desc")
                            content = (desc["text"][:100] + "...") if desc and desc.get("text") else "无文字内容"
                            
                            msg = {
                                "msg_type": "post",
                                "content": {
                                    "post": {
                                        "zh_cn": {
                                            "title": f"【B站新动态】{author}",
                                            "content": [
                                                [{"tag": "text", "text": f"UP主：{author}\n"}],
                                                [{"tag": "text", "text": f"内容：{content}\n"}],
                                                [{"tag": "a", "text": "👉 点击查看", "href": f"https://t.bilibili.com/{dynamic_id}"}]
                                            ]
                                        }
                                    }
                                }
                            }
                            if FEISHU_WEBHOOK:
                                res = requests.post(FEISHU_WEBHOOK, json=msg)
                                if res.status_code == 200:
                                    print(f"✅ 已推送 {author} 的新动态")
                                else:
                                    print(f"❌ 飞书推送失败: {res.text}")
                        new_last_ids[uid] = dynamic_id
                    else:
                        new_last_ids[uid] = ""
                    break
                else:
                    print(f"⚠️ UID {uid} B站返回业务错误: code={data['code']}")
            else:
                print(f"⚠️ UID {uid} 请求失败: {resp.status_code} - {resp.text[:100]}")
                
        except Exception as e:
            print(f"❌ UID {uid} 第 {attempt+1} 次尝试失败: {e}")
            time.sleep(2)  # 重试前等待
    
    if not success:
        new_last_ids[uid] = last_ids.get(uid, "")  # 保留旧ID，避免丢失

# 保存最新ID
with open(LAST_IDS_FILE, "w") as f:
    json.dump(new_last_ids, f, indent=2, ensure_ascii=False)

print("✅ 检查完成" + ("，发现新动态！" if has_new else "，暂无新动态。"))
