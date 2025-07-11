# 1Click 海外转化框架

这是一个模块化框架，用于将中国在线网店页面（如阿里巴巴1688）转换为适合在国际电子商务平台（如Shopee、Shopify等）上部署的结构化格式。

该框架旨在自动化以下流程：
- 从中国电子商务网站提取（抓取）产品数据
- 翻译和转换数据
- 准备数据以便无缝在全球平台上发布

## 功能特点

- 具有`Slice`和`Pipeline`类的模块化架构，用于数据提取
- 自动管道注册机制
- 使用`crawl4ai`进行无头浏览器自动化
- 具有进度跟踪的多次中英文翻译
- 通过WebSocket API实时更新进度
- 用于测试提取和翻译的交互式演示界面
- 灵活的数据处理与前/后处理器
- 输出结构化产品数据的JSON格式

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/1click_oversea.git
cd 1click_oversea
```

2. 创建并激活虚拟环境：
```bash
# 如果尚未安装uv，请先安装
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/bin/activate
```

3. 安装依赖：
```bash
# 从锁定文件安装依赖
uv sync --frozen
```

## 使用方法

在运行主脚本之前，您需要创建一个用户数据目录，供crawl4ai用于基于身份的爬取：

1. 使用[crawl4ai文档](https://docs.crawl4ai.com/advanced/identity-based-crawling/)中描述的方法之一创建用户数据目录：

```bash
# 首先找到Playwright Chromium二进制路径
python -m playwright install --dry-run

# 然后启动Chromium并指定自定义用户数据目录
# 将下面的路径替换为上一个命令中的实际路径
~/.cache/ms-playwright/chromium-1234/chrome-linux/chrome \
    --user-data-dir=/path/to/my_chrome_profile

# 在macOS上：
# ~/Library/Caches/ms-playwright/chromium-1234/chrome-mac/Chromium.app/Contents/MacOS/Chromium \
#     --user-data-dir=/Users/<you>/my_chrome_profile

# 在Windows上：
# "C:\Users\<you>\AppData\Local\ms-playwright\chromium-1234\chrome-win\chrome.exe" ^
#     --user-data-dir="C:\Users\<you>\my_chrome_profile"
```

2. 编辑`lib/pipelines/alibaba_1688.py`文件，将`user_data_dir`路径更新为您新创建的目录。

3. 运行主脚本以从阿里巴巴1688提取数据：

```bash
usage: main.py [-h] [--pipeline PIPELINE] --url URL [--headless] [--dump_to DUMP_TO] [--translate]
               [--translated_output TRANSLATED_OUTPUT] [--wait_for WAIT_FOR]

运行产品提取管道。

选项：
  -h, --help            显示帮助信息并退出
  --pipeline PIPELINE   要使用的管道名称（默认：alibaba_1688）
  --url URL             要抓取的产品URL
  --headless            在无头模式下运行浏览器
  --dump_to DUMP_TO     输出文件位置（如果设置，也会打印）
  --wait_for WAIT_FOR   返回HTML前的延迟秒数（默认：10）
  --translate           将产品数据翻译成英文
  --translated_output TRANSLATED_OUTPUT
                        翻译数据的输出文件（如果未指定，默认为[原始文件名]_translated.json）
```

   a. 首次运行脚本时，使用有头模式（不带`--headless`标志）登录1688.com：
   ```bash
   python main.py --pipeline alibaba_1688 --url https://detail.1688.com/offer/865196865369.html --dump_to data/example_product_data.json
   ```

   b. 当浏览器打开时，登录您的1688.com账户。凭据将保存在您的用户数据目录中。

   c. 对于后续运行，您可以使用无头模式以获得更快的处理速度：
   ```bash
   python main.py --pipeline alibaba_1688 --url https://detail.1688.com/offer/865196865369.html --dump_to data/example_product_data.json --headless
   ```

   d. 要将产品数据翻译成英文，添加`--translate`标志：
   ```bash
   python main.py --pipeline alibaba_1688 --url https://detail.1688.com/offer/865196865369.html --dump_to data/example_product_data.json --headless --translate
   ```

   e. 要提高性能，可以使用`--wait_for`参数调整抓取延迟时间：
   ```bash
   # 使用较短的延迟（2秒而不是默认的10秒）
   python main.py --pipeline alibaba_1688 --url https://detail.1688.com/offer/865196865369.html --headless --wait_for 2
   ```

   `wait_for`参数控制crawl4ai中的`delay_before_return_html`设置，该设置决定在捕获最终HTML之前等待多长时间。根据crawl4ai文档，默认值为0.1秒，但对于1688.com这样的复杂网站，我们使用较高的默认值（10秒）以确保所有动态内容正确加载。

   - **较低值（1-2秒）**：处理速度更快，但可能错过一些动态内容
   - **较高值（5-10秒）**：内容提取更可靠，但处理速度较慢

   其他具有不同布局的产品示例：
   ```
   # https://detail.1688.com/offer/718654342849.html
   # https://detail.1688.com/offer/802350325795.html
   # https://detail.1688.com/offer/640756097760.html
   # https://detail.1688.com/offer/764286652699.html
   ```

4. 提供API端点以便与其他应用程序集成：

   a. 启动FastAPI服务器：
   ```bash
   python serv.py
   ```

   b. 在浏览器中打开演示界面：
      - http://localhost:8000/demo - 用于测试提取和翻译的交互式演示UI

   c. API将提供以下端点：
      - `/api` - 关于API的基本信息
      - `/extract` - 从URL提取产品数据
      - `/job_status/{job_id}` - 检查翻译任务的状态
      - `/ws/extract` - 用于实时提取和翻译更新的WebSocket端点

   d. 使用curl的API使用示例：
   ```bash
   # 使用默认设置提取URL的数据（pipeline=alibaba_1688，wait_for=2）
   curl -X GET "http://localhost:8000/extract?url=https://detail.1688.com/offer/865196865369.html"

   # 提取并翻译数据（返回一个job_id用于轮询）
   curl -X GET "http://localhost:8000/extract?url=https://detail.1688.com/offer/865196865369.html&translate=true"

   # 检查翻译任务状态
   curl -X GET "http://localhost:8000/job_status/{job_id}"

   # 使用自定义等待时间（1秒）提取数据
   curl -X GET "http://localhost:8000/extract?url=https://detail.1688.com/offer/865196865369.html&wait_for=1"
   ```

   e. API默认以无头模式运行，等待时间较短（2秒），以获得更好的性能。这适用于不需要浏览器UI的生产环境。

## 翻译功能

该框架包含一个专为电子商务产品数据设计的强大中英文翻译系统：

- **智能字段检测**：自动识别哪些字段应该被翻译，哪些应该保持不变（例如SKU、尺寸、URL）
- **多次处理**：使用多次传递确保所有项目都被翻译，即使在初始尝试中有些被遗漏
- **分块处理**：以可管理的块处理数据，有效处理大型产品数据集
- **详细状态跟踪**：每个字段都标有其翻译状态：
  - `TRANSLATED`：成功从中文翻译成英文
  - `NOT_NEEDED`：识别为不需要翻译（例如数字、代码）
  - `MISSED`：多次尝试后未能翻译
- **实时进度更新**：使用WebSocket API时，在翻译过程中接收逐块进度更新

## 交互式演示UI

该框架包含一个基于浏览器的演示界面，用于测试提取和翻译：

1. 启动服务器：`python serv.py`
2. 在浏览器中打开 http://localhost:8000/demo
3. 输入产品URL
4. 选择翻译选项和等待时间
5. 选择WebSocket（实时更新）或REST API提取
6. 实时查看提取进度
7. 并排查看原始数据和翻译后的数据

## 项目结构

- `lib/`：核心框架组件
  - `pipeline.py`：用于编排数据提取的Pipeline类
  - `slice.py`：用于定义提取单元的Slice类
  - `registry.py`：用于管道管理的注册表
  - `translate.py`：中英文转换的翻译功能
  - `prompts.py`：翻译AI的系统提示
  - `pipelines/`：各种管道实现
    - `alibaba_1688.py`：1688.com特定的管道
- `utils/`：实用脚本
  - `highlight.js`：用于高亮元素的JavaScript
  - `simHover.js`：用于模拟悬停事件的JavaScript
- `static/`：前端资源
  - `index.html`：用于提取和翻译测试的演示UI
- `data/`：提取数据的输出目录
- `main.py`：运行提取的CLI脚本
- `serv.py`：带有WebSocket支持的API服务器

## 创建自定义管道

1. 在`lib/pipelines/`目录中创建新文件
2. 定义切片配置和后处理功能
3. 创建并注册管道工厂函数：

```python
@PipelineRegistry.register_pipeline(name="your_pipeline_name")
def create_your_pipeline():
    pipeline = Pipeline(name="YourPipeline", configs=YOUR_CONFIG)
    return pipeline
```

4. 在`lib/pipelines/__init__.py`中导入管道模块

## 局限性

- **视频URL**：`product_images`切片标记视频为`is_video`，但不提取视频URL。
- **动态SKU数据**：SKU部分的价格和库存可能随用户交互而变化；仅提取初始值。
- **用户交互**：需要点击、悬停或滚动的数据可能无法完全提取，因为未完全实现交互模拟。

## 许可证

MIT
