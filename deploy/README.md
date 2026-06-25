# Linux 云服务器部署

推荐把程序放在 `/opt/ai-career-viz`，把 SQLite 数据放在
`/var/lib/ai-career-viz/ai_career.db`。应用通过 `APP_DB_PATH` 显式绑定数据库位置。

```bash
sudo useradd --system --home /opt/ai-career-viz --shell /usr/sbin/nologin ai-career
sudo mkdir -p /opt/ai-career-viz /var/lib/ai-career-viz
sudo chown -R ai-career:ai-career /opt/ai-career-viz /var/lib/ai-career-viz

cd /opt/ai-career-viz
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
APP_DB_PATH=/var/lib/ai-career-viz/ai_career.db .venv/bin/python scripts/init_database.py

sudo cp deploy/ai-career-viz.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-career-viz
```

如由容器或平台托管，可把持久化卷挂载到 `/var/lib/ai-career-viz`，或将
`APP_DB_PATH` 指向平台提供的持久化目录。不要把云端数据库写进只读镜像层。

