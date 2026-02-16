# 可视化系统安装指南

## 快速安装

### 1. 安装依赖

```bash
pip install streamlit streamlit-echarts pyecharts
```

### 2. 启动应用

```bash
# 方式一：使用启动脚本
./start_streamlit.sh

# 方式二：直接运行
streamlit run web/streamlit_app.py
```

### 3. 访问界面

浏览器自动打开 http://localhost:8501

## 完整安装

```bash
# 安装所有依赖
pip install -r requirements.txt
```

## 验证安装

```bash
python -c "import streamlit; import pyecharts; print('安装成功！')"
```

## 常见问题

### Q: 提示缺少模块
A: 运行 `pip install -r requirements.txt`

### Q: 端口被占用
A: Streamlit 默认使用 8501，可通过 `streamlit run web/streamlit_app.py --server.port 8502` 更改端口

### Q: 图表不显示
A: 检查数据格式，确保包含必要的列（日期、开盘、收盘等）
