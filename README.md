
# 🛠️ 报价机器人 (Handy-Bot) 完整搭建文档

## 第一阶段：前期准备与账号开通

### 1. 准备数据源 (Google Sheets)
* **账号开通**：使用标准的 Google 账号（Gmail）登录 Google Drive。
* **建表**：新建一个 Google Sheets 表格，命名为 `handy-commands`（或其他易记名称）。
* **表头设置**：在第一行依次填入：`Service_Item`, `Unit`, `Base_Price(CAD)`, `Difficulty_Factor`, `Min_Fee(CAD)`。
* **录入数据**：填入对应的单价和难度系数规则。此表格将作为整个机器人的唯一价格计算依据。

测试用的google sheet 在,也可以要求AI帮你生成更多的测试数据

### 2. 获取通讯接口 (Telegram)
* **账号开通**：下载 Telegram App 并使用手机号注册。
* **创建 Bot**：
1. 在 Telegram 搜索栏输入 `@BotFather`。
2. 发送指令 `/newbot`。
3. 按照提示输入机器人的显示名称（如：Leo Handy Quote）和唯一用户名（必须以 `bot` 结尾，如 `leo_handy_bot`）。
4. 成功后，BotFather 会发送一串 **HTTP API Token**（如 `12345:ABCDE...`）。请妥善复制并保存此串代码，后续发布时需要用到。
* **设置菜单**：发送 `/setcommands` 给 BotFather，选择你的机器人，并发送以下文本建立快捷菜单：
```text
help - How to use this bot
price_list - View the full price list
```

开通测试bot截图


### 3. 注册逻辑引擎 (Coze)

* **账号开通**：访问 Coze.com 官网，使用 Google 账号或手机号完成注册并登录。
* **创建空间**：在左侧导航栏点击 **Workspace**，新建一个项目空间。

Coze免费用户每天有10个credit，如果选择便宜够用的的大模型(GPT-4o mini)，可以调用100次。 在coze界面左下角点击credit图标，在弹出的subscription plan选择的时候有每个模型的调用价格和每日次数限制。

---

## 第二阶段：核心工作流 (Workflow) 搭建

在 Coze 工作空间内点击左边菜单的Library, 再选页面中间上方的Workflow菜单，点击右上角紫色的 **+Resources** -> **Workflow**， 选择名字，填写功能描述，点击紫色confirm按钮生成一个空白workflow，并进入编辑页面。


按照以下顺序拖拽节点并配置：

### 节点 1：Start (起点)
* **作用**：接收用户在 Telegram 发送的消息或图片。
* **配置**：系统默认会有一个 `USER_INPUT` 变量，类型为 `String`，保持默认即可。

### 节点 2：Condition (条件分流)
* **作用**：拦截用户的指令文本，避免文字进入图片识别流程。
* **配置**：
* **Condition 1**：选择 `Start.USER_INPUT`，判断条件选择 **Contains**，输入值填入 `/help`。
* **Condition 2**：选择 `Start.USER_INPUT`，判断条件选择 **Contains**，输入值填入 `/price_list`。
* **Else**：保持默认，用于处理正常发图片估价的请求。

### 节点 3 & 4：Code (指令文本输出)
* **作用**：针对 `/help` 和 `/price_list` 输出固定话术。
* **连线**：将 Condition 1 连至 Code_1，Condition 2 连至 Code_2。
* **输入 (Input)**：**全部留空**（删掉系统默认的变量）。
* **输出 (Output)**：手动点击 `+`，添加变量名 `message`，类型选 `String`。
* **Code_1 代码 (`/help`)**： 

注意python代码的逻辑块靠tab键缩进区分，所以要保持缩进，否则会报错。

```python
def main(args):
	return {"message": "🛠️ **Handy-Bot Help**\n\nSend me a photo of your driveway/sidewalk, and tell me the depth of the snow (e.g. 15cm) to get an instant quote in CAD."}
```

* **Code_2 代码 (`/price_list`)**：

```python
def main(args):
	return {"message": "📋 **Price List**\n\n- Single Driveway: $30/visit\n- Double Driveway: $50/visit\n- Sidewalk: $20/visit\n*(+30% for snow > 15cm)*"}
```

### 节点 5：LLM (大语言模型识别)
* **连线**：将 Condition 的 `Else` 分支连至 LLM 节点。
* **模型选择**：选择 **GPT-4o mini**（确保具备视觉识别能力）。
* **输入设置**：引用 `Start.USER_INPUT`。
* **Prompt (提示词) 设置**：明确要求模型提取图片中的服务项目、数量，并以严格的 JSON 格式输出。

提示词分两部分：
* System Prompt

```text
Role: You are a professional estimator for residential services (Snow Removal & Tool Rental) in North America.

Identification Logic:

1. Snow Removal: Estimate the area (e.g., Single/Double Driveway, Sidewalk) and depth. If snow depth looks >15cm, set is_heavy_snow to true.
2. Tool Rental: Identify the tool (e.g., Nail Gun, Mower) and its condition.


Output Format (Strict JSON):

{
  "service_item": "string (e.g., Snow_Double_Driveway)",
  "quantity": 1,
  "is_difficult": boolean,
  "reason": "Short explanation for the customer"
}
```

* User Prompt

```text
Task: Please analyze this: {{input}} and provide the quote.
```

### 节点 6：Plugin - Google Sheets (读取表格)
* **连线**：紧接在 LLM 节点之后。
* **选择插件**：搜索并添加 `Google Sheets` -> `getSpreadsheet` 动作。
* **授权**：点击节点上的授权按钮，绑定你的 Google 账号。
* **配置参数**：
* `spreadsheetId`：填入你表格 URL 中的长串 ID。
* `range`：填入数据范围，如 `Sheet1!A1:E1000`。

### 节点 7：Code (核心计算逻辑)
* **连线**：接收 LLM 的识别结果和 Google Sheets 的数据。
* **输入 (Input)**：
* `identified_item` (String)：引用 LLM 节点的输出。
* `price_list` (Object/String)：引用 Google Sheets 节点的输出。
* **输出 (Output)**：添加 `message` (String)。
* **代码内容** 在 coze_code.py 里面，ai帮忙写的


### 节点 8：End (终点展示)
* **连线**：将 Code_1, Code_2, 和核心计算 Code 节点的输出，全部连至此 End 节点。
* **输入 (Input)**：
* `help` (String)：引用 Code_1 的输出变量message。
* `price_list` (String)：引用 Code_2 的输出变量message。
* `estimate` (String)：引用 Code 的输出变量message。
* **配置 Response**：
1. 清空输入框内所有文本。
2. 使用快捷键 `{` 唤出变量菜单。
3. 依次点击选中三个输入变量`{{help}}{{price_list}}{{estimate}}`。
4. 确保输入框内显示为三个紧挨着的彩色气泡块，中间**不要**加空格或回车。

---

## 第三阶段：绑定 Agent 与发布上线

### 1. 组装 Agent
* 在 Coze 左侧导航栏点击 **Home** 或 **Development**。
* 新建一个 **Agent**（机器人）并命名。
* 在 Agent 编辑页面的 `Arrangement` 区域，点击 **+ Click to add chatflow**，选中你刚才搭建好的 Workflow。

### 2. 配置 Telegram 渠道
* 点击 Agent 页面右上角的紫色 **Publish** 按钮。
* 在发布页面下拉找到 **Channels** 模块。
* 找到 **Telegram**，点击 **Configure**。
* 粘贴第一阶段在 BotFather 处获取的 **HTTP API Token** 并保存。
* **关键：** 勾选 Telegram 选项左侧的复选框。

### 3. 正式发布
* 点击页面右上角的最终 **Publish** 按钮。
* 打开你的 Telegram，找到你的机器人，发送 `/help` 或一张带雪的图片，系统即可自动回复。
