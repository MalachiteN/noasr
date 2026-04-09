# noasr — 人类测试指南

自动化测试（351 个 pytest）验证了所有模块的 mock 交互，但无法验证：
- MiMo Omni 是否真的接受我们发送的音频格式
- 录音设备是否正常工作
- 热键是否能被系统级捕获
- 剪贴板粘贴是否真正输出到目标应用
- LLM 返回的文本是否合理

**以下测试只有人类能做。**

---

## 前置条件

1. Windows 10/11（MVP 优先平台）
2. 麦克风设备已连接并启用
3. MiMo Omni API Key（从小米开放平台获取）
4. Python 3.12+ 已安装

---

## 第一步：安装

```powershell
cd C:\path\to\noasr
uv pip install -e . --python .venv\Scripts\python.exe
```

验证安装：
```powershell
.venv\Scripts\python -m noasr --version
# 应输出: noasr 0.1.0
```

---

## 第二步：首次启动（配置引导）

```powershell
.venv\Scripts\python -m noasr
```

首次运行会：
- 创建 `~/.noasr/` 目录
- 拷贝模板配置文件
- **立即退出**，提示你编辑配置

预期输出：
```
⚠️  First run detected! Configuration templates have been created.
   Please review and edit: C:\Users\<你>\.noasr
   Then run noasr again.
```

---

## 第三步：填写 API 配置

编辑 `C:\Users\<你>\.noasr\config.json`：

```json
{
  "baseurl": "https://api.mi-fds.com/v1",
  "api_key": "sk-你的真实APIKey",
  "toolsets": {
    "default": ["GetCurrentDateTime"]
  },
  "agents": [
    {
      "name": "dictate",
      "trigger": [62, 62],
      "toolsets": ["default"],
      "system_prompt_file": "input_system_prompt.md",
      "user_prompt_file": "input_user_prompt.md"
    }
  ]
}
```

> **trigger [62, 62]** 对应键盘上的 **F4** 键的虚拟键码。按住 F4 录音，松开发送。

---

## 第四步：编辑提示词（可选但推荐）

### 系统提示词
编辑 `~/.noasr/input_system_prompt.md`（默认为空，可以写）：

```markdown
你是一个语音输入助手。将用户提供的音频准确转录为文字。
只输出转录结果，不要添加任何解释或前缀。
```

### 用户提示词
编辑 `~/.noasr/input_user_prompt.md`（默认有模板）：

```markdown
You are a voice input assistant. Convert the provided audio to text accurately.
```

> 两个提示词文件都会被 AgentManager 在每次 LLM 调用时读取，修改后立即生效，无需重启。

---

## 第五步：配置正则后处理（可选）

编辑 `~/.noasr/regex.json`：

```json
{
  "把(.+?)替换成(.+?)": "将$1替换为$2",
  "换行": "\n"
}
```

规则按 JSON 键的顺序依次应用，`$1`/`$2` 映射到捕获组。

---

## 第六步：正式运行

```powershell
.venv\Scripts\python -m noasr
```

预期输出：
```
noasr v0.1.0 - Voice input using MiMo Omni
Press configured trigger key to start recording.
```

程序现在在前台运行，监听热键。

---

## 测试场景

### 场景 1：基础语音听写

1. 打开任意文本编辑器（记事本、VS Code、浏览器输入框等）
2. **按住 F4**
3. 屏幕底部应出现黑色胶囊状覆盖层，显示 "● 0:00" 并计时
4. 对着麦克风说一句清晰的话，例如："今天天气不错"
5. **松开 F4**
6. 覆盖层切换为 "⏳ 处理中..."
7. 等待 2-5 秒（取决于网络）
8. 转录文本应自动粘贴到当前焦点输入框中

**检查点：**
- [ ] 按住 F4 时覆盖层出现
- [ ] 覆盖层计时正常递增
- [ ] 松开后覆盖层显示 "处理中"
- [ ] 文本成功粘贴到目标应用
- [ ] 粘贴后剪贴板内容恢复（如果之前有内容）

### 场景 2：录音时长限制

1. 按住 F4 保持 30 秒以上
2. 程序应在约 30 秒时自动停止录音并发送
3. 不应无限录音

**检查点：**
- [ ] 30 秒后自动停止
- [ ] 仍然正常粘贴结果

### 场景 3：过短录音

1. 快速按一下 F4（按住不到 0.3 秒）
2. 录音应被丢弃
3. 程序回到空闲状态

**检查点：**
- [ ] 无文本粘贴
- [ ] 程序继续正常运行，不卡死

### 场景 4：工具调用（ReAct 循环）

1. 修改 `~/.noasr/input_system_prompt.md`：
   ```markdown
   你是一个语音助手。用户可能问你时间。如果问时间，使用工具获取当前时间后回答。
   ```
2. 重启 noasr
3. 按住 F4，说："现在几点了？"
4. 松开
5. LLM 应调用 GetCurrentDateTime 工具获取时间，然后返回包含时间的回答

**检查点：**
- [ ] 工具被调用（stderr 日志中可见 tool_calls）
- [ ] 最终文本包含当前时间
- [ ] 时间文本被粘贴到输入框

### 场景 5：正则后处理

1. 编辑 `~/.noasr/regex.json`：
   ```json
   {
     "你好": "Hello"
   }
   ```
2. 重启 noasr
3. 按住 F4，说："你好"
4. 粘贴的文本应该是 "Hello" 而不是 "你好"

**检查点：**
- [ ] 正则替换生效
- [ ] 未匹配的文本保持原样

### 场景 6：单实例锁

1. 在第一个终端运行 noasr
2. 打开第二个终端，再次运行 noasr
3. 第二个实例应报错退出

**检查点：**
- [ ] 第二个实例输出 "Another instance of noasr is already running."
- [ ] 第一个实例继续正常运行

### 场景 7：Ctrl+C 退出

1. 运行 noasr
2. 按 Ctrl+C
3. 程序应干净退出

**检查点：**
- [ ] 输出 "Shutting down noasr..."
- [ ] 无异常堆栈
- [ ] 再次启动时不会提示 "already running"

---

## 查看 LLM 请求/响应日志

noasr 将所有 MiMo API 请求和响应输出到 stderr。在 PowerShell 中重定向到文件查看：

```powershell
.venv\Scripts\python -m noasr 2>noasr_debug.log
```

日志格式：
```
[MiMo REQUEST] { "model": "xiaomi/mimo-v2-omni", "messages": [...], ... }
[MiMo RESPONSE] { "id": "...", "choices": [...], ... }
```

> **注意**：日志中包含完整的消息内容，可能包含你的音频 data URI（很长的 base64 字符串）和 LLM 输出。不要将日志分享给他人。

---

## 常见问题

### 按住 F4 没反应
- 检查 stderr 是否有 "Failed to start hotkey listener"
- 某些应用（如管理员权限的应用）可能拦截全局热键
- 尝试在记事本中测试

### 没有覆盖层出现
- stderr 中搜索 "overlay" 相关错误
- Flet 可能需要 GPU 驱动支持
- 程序仍然可以无覆盖层工作，只是缺少视觉反馈

### 录音但无文本输出
- 检查 API Key 是否正确
- 检查 baseurl 是否可达（`curl https://api.mi-fds.com/v1`）
- 查看 stderr 日志中的 [MiMo RESPONSE] 错误信息
- 确认麦克风设备正常（Windows 设置 → 隐私 → 麦克风权限）

### 文本未粘贴到目标应用
- 确认目标输入框有焦点（光标闪烁）
- 某些 UAC 提权应用不接受模拟粘贴
- 检查 stderr 中 "injection" 相关错误

### API 返回错误
- `401`: API Key 无效
- `429`: 请求频率过高
- `500`: MiMo 服务端问题
- 检查 stderr 日志中的 [MiMo RESPONSE] 获取详细错误

---

## 配置文件结构

```
~/.noasr/
├── config.json              # 主配置（API Key、Agent 定义）
├── input_system_prompt.md   # 系统提示词
├── input_user_prompt.md     # 用户提示词
├── regex.json               # 正则后处理规则
└── .noasr.lock              # 单实例锁（自动管理，勿手动删除）
```

## 当前架构

```
用户按住 F4
  → HotkeyListener (pynput) 捕获按键
  → NoasrRuntime._on_key_down()
    → AudioRecorder.start() (sounddevice 录音)
    → OverlayController.show_listening()

用户松开 F4
  → NoasrRuntime._on_key_up()
    → AudioRecorder.stop_and_normalize() → WAV bytes → base64 data URI
    → NoasrRuntime._process_recording(audio_data_uri)
      → AgentManager.run_agent("dictate", audio_data_uri, client)
        → load_agent_prompts() 读取提示词
        → AudioPayload.to_api_item() 构建音频消息
        → MiMoClient.send() 发送请求
        → ReAct 循环（如果 LLM 返回 tool_calls）
          → ToolManager.execute_tool() 执行工具
          → 再次 MiMoClient.send()
        → 返回最终文本
      → RegexProcessor.apply() 正则后处理
      → TextInjector.inject() 保存剪贴板 → 粘贴 → 恢复剪贴板
    → _reset_to_idle()
```
