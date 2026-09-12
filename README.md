# A 股短线筛选器

极简、低资源占用的 FastAPI 基础工程。Phase 2 仅加入腾讯单股/少量股票实时行情验证，**不包含全市场扫描、行情历史、指标或选股策略**。

## 项目结构

```text
app/          FastAPI 应用、模板、静态资源及预留业务包
data/         SQLite 数据目录（数据库文件不提交）
scripts/      更新部署脚本
systemd/      Ubuntu systemd 服务示例
requirements.txt
```

## Ubuntu 首次部署

服务器需安装 Git 和 Python 3.11 或更高版本（包括 `venv` 模块）：

```bash
sudo apt update
sudo apt install -y git python3 python3-venv
git clone <你的仓库地址> a-share-screener
cd a-share-screener
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 手动启动

```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 `http://服务器地址:8000/`，或使用 `curl http://127.0.0.1:8000/health` 检查服务。应用启动时会自动创建 `data/screener.db` 及 `metadata` 表。

## 腾讯实时行情

首页可输入沪深六位代码查询。单股接口为 `GET /api/quote/{code}`；`GET /api/debug/tencent-benchmarks` 会依次验证 `600519`、`000001`、`002130`、`002897`。后端使用 Python 标准库 `urllib` 访问 `https://qt.gtimg.cn/q=`，不增加 HTTP 客户端依赖，并将 GB18030 响应转换为 Unicode。

腾讯 Web 行情接口不是正式开发者 API，字段布局未来可能变化。因此项目对价格、换手率、量比、市值关系等字段执行 sanity check，并使用 fail-closed 保护：网络错误、字段缺失、解析失败或数值异常时均返回 `status: "unavailable"`，不会用 `0` 冒充未知值。

## 安装 systemd 服务

将示例中的 `<PROJECT_DIR>` 替换为项目的实际绝对路径后安装。路径可按服务器环境配置，示例没有写死用户或目录：

```bash
sed "s|<PROJECT_DIR>|$(pwd)|g" systemd/a-share-screener.service.example \
  | sudo tee /etc/systemd/system/a-share-screener.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now a-share-screener
sudo systemctl status a-share-screener
```

服务以单 worker 运行，并会在异常退出后自动重启。

## 更新代码

安装好 systemd 服务后，在项目目录执行：

```bash
./scripts/deploy.sh
```

脚本会以 fast-forward 模式拉取代码、按需创建 `.venv`、安装依赖并重启服务。如服务使用了不同名称，可执行 `SERVICE_NAME=你的服务名 ./scripts/deploy.sh`。

## 安全说明

不要向 GitHub 提交密码、Token、SSH 私钥、`.env` 或 SQLite 数据库。敏感配置应仅保存在服务器，并通过权限受控的环境文件或 systemd 配置注入；仓库只应提供不含真实凭据的 `.env.example`。
