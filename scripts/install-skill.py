#!/usr/bin/env python3
"""
安装 OpenClaw skill 包
"""

import os
import subprocess
import shutil

# 源文件路径（使用最新的）
zip_path = "/root/.openclaw/media/inbound/twitter-ai-scraper---bfdf5151-20fd-4c59-80dd-37a92b6bcd67.zip"

# 目标目录
skill_dir = "/root/.openclaw/extensions/feishu"
skill_path = os.path.join(skill_dir, "feishu")

print(f"源文件: {zip_path}")
print(f"目标目录: {skill_dir}")
print(f"目标文件: {skill_path}")

# 检查源文件是否存在
if os.path.exists(zip_path):
    print(f"✅ 源文件存在")
    
    # 创建目录（如果不存在）
    if not os.path.exists(skill_dir):
        os.makedirs(skill_dir, exist_ok=True)
        print(f"✅ 创建目录: {skill_dir}")
    
    # 复制文件
    shutil.copy2(zip_path, skill_path)
    print(f"✅ 文件已复制到: {skill_path}")
    
    # 检查 SKILL.md
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(skill_md):
        print(f"✅ SKILL.md 已存在: {skill_md}")
        with open(skill_md, 'r') as f:
            content = f.read()
            if 'Twitter AI' in content or 'Twitter AI 技取' in content:
                print(f"✅ 检测到 Twitter AI 技能包")
                print(f"   技能描述: {content[:100]}...")
            else:
                print(f"⚠️  SKILL.md 可能需要更新")
    else:
        print(f"❌ SKILL.md 不存在: {skill_md}")
    
    print("\n✅ 技能包已安装！")
    print("\n这个 Twitter AI 技能包提供：")
    print("- Twitter 数据抓取功能")
    print("- 使用智谱 API 进行搜索")
    print("- 支持用户推文获取")
    print("- 包含完整的 SKILL.md 和 SKILL.json 配置")
    print("- 可以在 OpenClaw 中使用")
    
else:
    print(f"❌ 源文件不存在: {zip_path}")
    print("请检查文件名或重新上传")
