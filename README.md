# 生成式AI背景下职业演化与就业结构变化分析及可视化平台设计

项目将 1991—2025 年中国三次产业就业占比年度数据与 109,986 条中国招聘岗位公开样本
结合，分析生成式AI背景下的长期就业结构演化、2026—2030 年趋势预测、当前职业结构、
AI关联特征、职业任务结构、转型路径、城市分布、薪资和就业门槛。应用使用 Plotly、
SQLite 和 scikit-learn，采用“就业结构演化 → 招聘市场证据 → 区域分布差异 →
任务暴露与技能结构 → 结构趋势预测 → 职业转型路径”的递进式导航，先呈现现实数据，
再进行机制解释、趋势预测和转型情景推演，6 个主题页承载 11 个分析模块。

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_database.py
streamlit run app.py
```

仓库已包含清洗后的 `data/china_jobs_clean.csv.gz`、官方年度序列
`data/china_employment_structure.csv` 和预生成的 `ai_career.db`。
数据库文件缺失时，应用会自动从压缩 CSV 重建。

## 数据来源

长期序列来自世界银行开放数据 API，指标为中国第一、第二、第三产业就业人员占比
（ILO 模型估计），覆盖 1991—2025 年。招聘数据来自 Kaggle 的
`BOSS_Zhipin_Sample_Data`，发布者为 `jeanshendev`，数据集页面
更新时间为 2025-04-18，许可证标注为 MIT。详细来源、文件摘要、清洗流程和数据边界见
[`data/README.md`](data/README.md)。

该数据为真实招聘岗位的公开便利样本，不是实时 API，发布者未提供明确采集日期。多数
城市约有 300 条记录，因此城市样本数不能解释为城市招聘总量。平台中的 AI 关联岗位由
职位名称、关键词和描述中的规则术语识别，不表示岗位替代风险。

任务与AI暴露页面使用职位名称、关键词和行业文本构造五项相对代理指标。重复性、创造性、
数字化强度和人际互动由对应术语命中率在13类职业内做Min-Max缩放；AI暴露代理指数综合
数字化强度、直接AI术语和可数字化重复任务。职业转型路径是能力迁移情景，不是对真实
劳动者流动的追踪数据。

2026—2030 年产业占比使用最近 12 年线性趋势外推，并进行五年滚动起点回测；阴影区间
根据回测残差计算。职业类别情景指数把当前招聘样本的产业构成映射到产业预测，表示
结构环境而非未来岗位数量、失业率或 AI 替代概率。

如需从原始 Excel 重新生成清洗数据：

```bash
pip install -r requirements-data.txt
python scripts/prepare_real_dataset.py --input BOSS_Zhipin_Sample_Data.xlsx
python scripts/init_database.py
```

如需更新官方年度序列：

```bash
python scripts/fetch_employment_trends.py
python scripts/init_database.py
```

## 数据库路径

路径选择集中在 `src/config.py`：

1. 设置 `APP_DB_PATH` 时始终使用指定路径。
2. macOS 和 Windows 本地运行时使用项目根目录 `ai_career.db`。
3. Linux 默认尝试 `/var/lib/ai-career-viz/ai_career.db`。
4. 系统目录不可写时回退到 `XDG_DATA_HOME` 或
   `~/.local/share/ai-career-viz/ai_career.db`。

自管 Linux 服务器部署说明见 [`deploy/README.md`](deploy/README.md)。

## Streamlit Community Cloud

1. 将项目提交到 GitHub；`.venv/`、`.work/`、缓存和 Secrets 已在 `.gitignore` 中排除。
2. 在 Streamlit Community Cloud 选择仓库、分支和入口文件 `app.py`。
3. Python 版本选择 `3.12`，平台会读取根目录 `requirements.txt`。
4. 本项目不需要 Secrets，也不需要在云端下载 Kaggle 数据。

Community Cloud 的实例文件系统不保证永久保存，但本项目的 SQLite 数据库属于可重建
缓存。实例重启后若数据库丢失，应用会从仓库中的压缩 CSV 自动初始化。以后若增加用户
收藏、标注或实时写入，应改用托管数据库，而不是实例本地 SQLite。

## 测试

```bash
python -m unittest discover -s tests -v
pip check
```
