import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def http_url_check(url, timeout=8):
    """精准HTTP流检测（增强版）"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        try:
            response = requests.head(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True
            )
            if response.status_code == 200:
                print(f"\n✅ HEAD验证成功: {url}")
                return True
        except requests.exceptions.HTTPError:
            pass

        with requests.get(
            url,
            stream=True,
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        ) as response:
            if response.status_code not in [200, 302]:
                return False

            content_type = response.headers.get('Content-Type', '')
            if 'video' in content_type or 'audio' in content_type:
                print(f"\n🎥 检测到媒体流: {url}")
                return True

            for i, chunk in enumerate(response.iter_content(chunk_size=128)):
                if i >= 4:
                    break
                if chunk:
                    return True

            return False

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败 {url}: {str(e)[:50]}")
        return False
    except Exception as e:
        print(f"\n⚠️ 未知错误 {url}: {str(e)[:50]}")
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

            start_time = time.time()
            futures = []

            with ThreadPoolExecutor(max_workers=20) as executor:
                # 提交所有验证任务
                for base_url in valid_urls:
                    for name, ip_port in matches:
                        new_url = f"{base_url.rstrip('/')}/udp/{ip_port}"
                        futures.append(
                            executor.submit(
                                process_channel,
                                name,
                                new_url
                            )
                        )

                # 实时进度跟踪
                total = len(futures)
                processed = 0
                valid_count = 0

                for future in as_completed(futures):
                    result = future.result()
                    processed += 1

                    if result:
                        final_content.append(result)
                        valid_count += 1
                        current_name = result.split(',')[0]
                    else:
                        current_name = "无效频道"

                    # 计算统计信息
                    elapsed = time.time() - start_time
                    speed = processed / elapsed if elapsed > 0 else 0
                    avg_speed = valid_count / elapsed if elapsed > 0 else 0

                    # 动态进度显示
                    print(
                        f"\r🚀 进度: {processed}/{total} | "
                        f"有效: {valid_count} | "
                        f"耗时: {elapsed:.1f}s | "
                        f"速度: {speed:.1f}条/秒 | "
                        f"最新: {current_name[:15]:<15}",
                        end="", flush=True
                    )

            print("\n✅ 验证完成")  # 换行保留最终状态

    except Exception as e:
        print(f"\n❌ 文件处理异常: {str(e)}")

    return final_content


def process_channel(name, url):
    """处理单个频道验证"""
    return f"{name},{url}" if http_url_check(url) else None
