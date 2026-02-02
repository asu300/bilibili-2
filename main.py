name: 检查B站UP主动态并推送到飞书

on:
  schedule:
    - cron: '*/20 * * * *'  # 每20分钟检查一次（UTC）
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest

    steps:
      - name: 检出代码
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}  # 👈 关键：赋予写权限

      - name: 设置 Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: 安装依赖
        run: pip install requests

      - name: 运行监控脚本
        env:
          FEISHU_WEBHOOK: ${{ secrets.FEISHU_WEBHOOK }}
          BILI_UIDS: ${{ secrets.BILI_UIDS }}
        run: python main.py

      - name: 提交 last_ids.json
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email '41898282+github-actions[bot]@users.noreply.github.com'
          git add last_ids.json
          git diff --staged --quiet && echo "✅ 无新动态" || git commit -m "chore: update last dynamic IDs"
          git push  # 👈 现在可以安全 push！
