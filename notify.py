def fetch_items_for_uid(uid: str, max_retries: int = 4, backoff_base: float = 1.0) -> list:
    """
    尝试从 polymer endpoint 获取 items 列表；在失败时做重试，并在必要时回退到 space_history 接口。
    返回 items 列表（可能为空）。
    """
    from json import JSONDecodeError
    # 简单的 UID 校验（若格式不对，提前返回）
    if not uid.isdigit() or len(uid) > 12:
        # 警告但仍尝试请求（有时 UID 长度不同），你也可以选择直接 return []
        print(f"⚠️ 可疑 UID 格式: {uid}")

    endpoints = [
        f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}",
        # 备用接口（常见）
        f"https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid={uid}&offset_dynamic_id=0&need_top=0",
    ]

    # 加强 headers：加 Referer 可能有助于通过简单反爬
    headers = {
        "User-Agent": HEADERS.get("User-Agent", "Mozilla/5.0 (bilibili-feishu-notifier)"),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"https://space.bilibili.com/{uid}",
    }

    for endpoint in endpoints:
        attempt = 0
        while attempt <= max_retries:
            try:
                attempt += 1
                resp = requests.get(endpoint, headers=headers, timeout=REQUEST_TIMEOUT)
                status = resp.status_code

                # 非 200，特殊处理 429/5xx 重试，4xx（除 429）通常不重试
                if status != 200:
                    snippet = (resp.text or "")[:200].replace("\n", " ")
                    print(f"⚠️ {endpoint} 返回 HTTP {status} (uid={uid}) snippet={snippet}")
                    if status in (429, 502, 503, 504):
                        # 若 header 中含 Retry-After 则尊重它
                        ra = resp.headers.get("Retry-After")
                        if ra and ra.isdigit():
                            wait = int(ra)
                        else:
                            # 指数回退 + 随机抖动
                            wait = backoff_base * (2 ** (attempt - 1)) + (0.1 * attempt)
                        print(f"⏳ 等待 {wait:.1f}s 后重试 (HTTP {status})")
                        time.sleep(wait)
                        continue
                    else:
                        # 对于 4xx（非 429）和其他非重试状态，跳出重试循环去尝试下一个 endpoint
                        break

                # 尝试解析为 JSON
                try:
                    data = resp.json()
                except JSONDecodeError:
                    snippet = (resp.text or "")[:500].replace("\n", " ")
                    print(f"❌ 解析 JSON 失败（uid={uid}, endpoint={endpoint}），响应前500字符: {snippet}")
                    # 若是空响应或 HTML，可能是临时问题或被拦截，做重试
                    if attempt <= max_retries:
                        wait = backoff_base * (2 ** (attempt - 1)) + (0.1 * attempt)
                        time.sleep(wait)
                        continue
                    else:
                        break

                # 检查返回格式并提取 items（兼容两个 endpoint 的结构）
                # polymer endpoint: data.get("data", {}).get("items")
                # space_history endpoint: data.get("data", {}).get("cards")
                items = None
                if isinstance(data, dict):
                    items = data.get("data", {}).get("items")
                    if items is None:
                        items = data.get("data", {}).get("cards")
                if not items:
                    # 兼容：部分接口会把 dynamic 列表放在 data.list/archives 等，若无则返回空
                    print(f"ℹ️ {endpoint} 返回空 items（uid={uid}）")
                    return []
                return items
            except requests.RequestException as e:
                # 网络/超时错误
                print(f"❌ 请求异常 uid={uid} endpoint={endpoint} attempt={attempt}: {e}")
                if attempt <= max_retries:
                    wait = backoff_base * (2 ** (attempt - 1)) + (0.2 * attempt)
                    time.sleep(wait)
                    continue
                else:
                    break
        # 如果当前 endpoint 多次失败，尝试下一个 endpoint（fallback）
        print(f"⚠️ endpoint {endpoint} 多次失败，尝试下一个备选接口（uid={uid}）")

    # 如果所有 endpoint 都尝试完且没有返回 items，返回空列表
    return []
