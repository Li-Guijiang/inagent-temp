# -*- coding: utf-8 -*-
"""打包 比赛演示包 目录为最终参赛压缩包（UTF-8 中文文件名安全）。"""
import os
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "比赛演示包")
OUT = os.path.join(ROOT, "命题188智能制造比赛演示包.zip")

ZIP_TOP = "命题188智能制造比赛演示包"  # 压缩包内顶层目录名


def collect(src, prefix):
    items = []
    for name in sorted(os.listdir(src)):
        full = os.path.join(src, name)
        rel = os.path.join(prefix, name)
        if os.path.isdir(full):
            # 跳过运行缓存之外的产物目录可保留（演示数据），全部打包保证自包含
            items.append((full, rel, True))
            items.extend(collect(full, rel))
        else:
            items.append((full, rel, False))
    return items


def main():
    if os.path.exists(OUT):
        os.remove(OUT)
    items = collect(SRC, ZIP_TOP)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        dirs_seen = set()
        for full, rel, is_dir in items:
            if is_dir:
                if rel not in dirs_seen:
                    zi = zipfile.ZipInfo(rel + "/")
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    zf.writestr(zi, b"")
                    dirs_seen.add(rel)
            else:
                zf.write(full, rel)
    size = os.path.getsize(OUT)
    print(f"打包完成：{OUT}")
    print(f"压缩包大小：{size/1024/1024:.2f} MB，总条目：{len(items)}")
    # 打印顶层结构
    with zipfile.ZipFile(OUT) as zf:
        tops = sorted({n.split('/')[0] + '/' + n.split('/')[1] for n in zf.namelist() if n.count('/') >= 1})
        print("压缩包内容（顶层）：")
        for t in tops:
            print("  " + t)


if __name__ == "__main__":
    main()