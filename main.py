import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def http_url_check(url, timeout=8):
    """精准HTTP流检测（增强版）"""
    try:
        # 添加通用User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # 先尝试HEAD请求（快速检测）
        try:
            response = requests.head(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True
            )
            if response.status_code == 200:
                print(f"✅ HEAD验证成功: {url}")
                return True
        except requests.exceptions.HTTPError:
            pass

        # 若HEAD不可用则尝试GET请求
        with requests.get(
            url,
            stream=True,  # 流模式不下载全部内容
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        ) as response:
            # 检查状态码和Content-Type
            if response.status_code not in [200, 302]:
                return False

            # 验证流媒体特征（至少读取前512字节）
            content_type = response.headers.get('Content-Type', '')
            if 'video' in content_type or 'audio' in content_type:
                print(f"🎥 检测到媒体流: {url}")
                return True

            # 若未明确类型则尝试读取数据
            for i, chunk in enumerate(response.iter_content(chunk_size=128)):
                if i >= 4:  # 读取512字节（4*128）
                    break
                if chunk:
                    return True

            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败 {url}: {str(e)[:50]}")
        return False
    except Exception as e:
        print(f"⚠️ 未知错误 {url}: {str(e)[:50]}")
        return False


def generate_final_list(valid_urls):
    """生成最终播放列表（带流媒体验证）"""
    final_content = []

    if not os.path.exists('gdNet.txt'):
        print("❌ 关键文件gdNet.txt缺失！")
        return []

    channel_pattern = re.compile(
        r'^(.*?),\s*rtp://(\d+\.\d+\.\d+\.\d+:\d+)$',
        re.MULTILINE
    )

    try:
        with open('gdNet.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            matches = channel_pattern.findall(content)

            if not matches:
                print("⚠️ gdNet.txt格式异常！")
                return []

            print(f"📺 发现 {len(matches)} 个电视频道")

            # 创建进度计数器
            total = len(valid_urls) * len(matches)
            processed = 0
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = []
                for base_url in valid_urls:
                    for name, ip_port in matches:
                        new_url = f"{base_url.rstrip('/')}/udp/{ip_port}"
                        futures.append(
                            executor.submit(
                                process_channel,
                                name,
                                new_url,
                                start_time,
                                total,
                                processed
                            )
                        )

                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        final_content.append(result)
                        processed += 1

    except Exception as e:
        print(f"❌ 文件处理异常: {str(e)}")

    return final_content


def process_channel(name, url, start_time, total, processed):
    """处理单个频道并显示实时进度"""
    if http_url_check(url):
        elapsed = time.time() - start_time
        speed = processed / elapsed if elapsed > 0 else 0
        print(
            f"\r🚀 进度: {processed+1}/{total} | "
            f"耗时: {elapsed:.1f}s | "
            f"速度: {speed:.1f}条/秒 | "
            f"最新有效: {name[:15]}",
            end="", flush=True
        )
        return f"{name},{url}"
    return None

