#!/usr/bin/env python3
# legado 缓存包缺图恢复脚本（本地运行，不受 CORS / Referer 限制）
# 用法:
#   python _legado_fetch.py dry                 -> 仅解析默认包 .nb，打印 URL，不下载
#   python _legado_fetch.py download            -> 下载默认包缺图
#   python _legado_fetch.py download 别的书.zip  -> 下载任意 legado 缓存包（按包名自动建输出目录）
#   python _legado_fetch.py dry 别的书.zip       -> 只解析指定包，不下载
import sys, re, os, json, time
import zipfile
from urllib import request

ZIP = r"C:\Users\23942\Desktop\幻影敢死队daea6e81275b7d83.zip"  # 默认包；命令行传其他 .zip 即覆盖

def out_dir_for(zip_path):
    """每个缓存包独立输出目录，避免不同书混在一起：<zip目录>/<zip名>_images"""
    d = os.path.dirname(zip_path) or '.'
    stem = os.path.splitext(os.path.basename(zip_path))[0]
    return os.path.join(d, stem + '_images')
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

def parse_nb_urls(zp):
    names = zp.namelist()
    nb = sorted([n for n in names if n.lower().endswith('.nb')])
    urls = []
    for n in nb:
        raw = zp.read(n).decode('utf-8', 'replace')
        # legado 把图源 JSON 直接塞进 src 属性值里（含未转义引号），
        # 所以不能按 " 截断，要抓到标签结尾的 "> 之前的全文
        for tag in re.finditer(r'<img\b[^>]*>', raw):
            t = tag.group(0)
            m = re.search(r'src="(.*)">', t, re.S)
            if not m:
                continue
            value = m.group(1)          # 形如 URL,{"headers":{"Referer":"..."}}
            comma = value.find(',')
            url = value[:comma].strip() if comma >= 0 else value.strip()
            referer = ''
            if comma >= 0:
                try:
                    referer = json.loads(value[comma+1:])['headers']['Referer']
                except Exception:
                    pass
            urls.append((url, referer))
    return urls

def download(url, referer, dest):
    req = request.Request(url, headers={'Referer': referer, 'User-Agent': UA,
                                        'Accept': 'image/avif,image/webp,image/*,*/*'})
    with request.urlopen(req, timeout=20) as r:
        data = r.read()
    with open(dest, 'wb') as f:
        f.write(data)
    return len(data)

def main():
    args = sys.argv[1:]
    explicit = None
    zip_path = ZIP
    for a in args:
        if a in ('dry', 'download'):
            explicit = a
        else:
            zip_path = a          # 把具体包路径传进来即可换书
    # 传了具体包但没写模式 -> 默认 download（贴合“直接 download 就能补回”）
    mode = explicit if explicit else ('download' if zip_path != ZIP else 'dry')
    out = out_dir_for(zip_path)

    zp = zipfile.ZipFile(zip_path, 'r')
    urls = parse_nb_urls(zp)
    zp.close()
    print('目标包:', zip_path)
    print('解析出图源 URL 总数:', len(urls))
    print('前 5 条:')
    for i, (u, r) in enumerate(urls[:5]):
        print(f'  {i+1}. {u}  (Referer={r})')

    if mode == 'dry':
        print('\n[dry] 未下载。确认后运行: python _legado_fetch.py download', zip_path)
        return

    os.makedirs(out, exist_ok=True)
    ok = fail = 0
    for i, (u, r) in enumerate(urls):
        dest = os.path.join(OUT, f'{i+1:03d}.jpg')
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            ok += 1; continue
        try:
            sz = download(u, r, dest)
            ok += 1
            print(f'\r  下载 {i+1}/{len(urls)} 成功{ok} 失败{fail} 大小{sz}', end='', flush=True)
        except Exception as e:
            fail += 1
            print(f'\n  #{i+1} 失败: {e}  {u}')
        time.sleep(0.2)
    print(f'\n完成: 成功 {ok}, 失败 {fail}')
    print('图片已存至:', out, '(按 001.jpg… 顺序)')

if __name__ == '__main__':
    main()
