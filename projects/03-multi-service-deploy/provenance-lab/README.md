# Creative Provenance Lab

一个面向 AIGC 与视觉创作流程的轻量溯源原型：导入图像后提取技术元数据、综合色彩和感知指纹，并以版本谱系和对比视图呈现迭代过程。

## 运行

```powershell
cd "D:\PORTFOLIO作品集\creative-scout-online-deploy\provenance-lab"
python -m pip install -r requirements.txt
python backend\server.py
```

打开 `http://localhost:8010`。

## 重要边界

- “视觉相似度”由感知哈希计算，只是一种图像近似信号，不能证明版权、作者或真实生成链路。
- EXIF 与 Prompt 元数据只有在文件实际携带时才能读取；缺失时会明确显示为“未提供”。
- Render 等无持久磁盘环境中的上传内容是临时的；预置演示谱系会在服务启动时自动恢复。
