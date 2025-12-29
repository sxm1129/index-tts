# IndexTTS API 服务部署指南

## 📋 概述

IndexTTS API 服务提供 REST API 接口，支持远程调用进行文字转语音。兼容 GLM-TTS API 参数格式，可无缝迁移。

## 🚀 快速启动

### 1. 启动 API 服务

使用 conda 环境启动：

```bash
conda activate xsmartvoice_env
cd /data1/workspace/index-tts
export HF_ENDPOINT="https://hf-mirror.com"
python api_server.py --fp16 --api_port 8050
```

### 2. 验证服务状态

```bash
curl http://localhost:8050/api/v1/health
```

预期响应：
```json
{
    "status": "healthy",
    "model_loaded": true,
    "model_version": "2.0",
    "device": "cuda:0",
    "fp16_enabled": true,
    "available_prompts": 28,
    "available_emotions": 2
}
```

### 3. 快速测试

```bash
curl -X POST http://localhost:8050/api/v1/tts \
  -F "input_text=你好，欢迎使用IndexTTS。" \
  -F "index=zh_female_intellectual" \
  -F "beam_size=1" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('成功:', d['success'], '时间:', d.get('generation_time'), '秒')"
```

## 📁 文件结构

```
/data1/workspace/index-tts/
├── api_server.py                    # FastAPI 主服务
├── configs/
│   ├── api_config.yaml             # API 服务配置
│   └── prompt_cache.json           # 音频索引映射
├── indextts/
│   └── api_handler.py              # API 业务逻辑
├── docs/
│   └── INDEXTTS_API_CLIENT_GUIDE.md # 客户端调用指南
└── examples/                        # 音频文件目录
    ├── 中文女声（*.mp3              # 16 个新增音色
    ├── 英文女声（*.mp3
    ├── voice_*.wav                  # 12 个原有音色
    └── emo_*.wav                    # 情感参考
```

## 🎛️ 服务配置

### 启动参数

```bash
python api_server.py [OPTIONS]

Options:
  --api_port PORT           API 服务端口 (默认: 8050)
  --api_host HOST          API 服务主机 (默认: 0.0.0.0)
  --config PATH            配置文件路径
  --prompt_cache PATH      索引配置文件路径
  --model_dir DIR          模型目录
  --fp16                   启用 FP16 加速
  --device DEVICE          指定设备 (cuda:0, cpu, etc.)
  --reload                 启用自动重载（开发模式）
```

### 配置文件

编辑 `configs/api_config.yaml` 自定义配置：

```yaml
# 并发控制
concurrency:
  max_concurrent_short: 3   # 短文本最大并发
  max_concurrent_medium: 2  # 中等文本最大并发
  max_concurrent_long: 1    # 长文本最大并发

# 生成默认参数
generation:
  temperature: 0.8
  top_p: 0.8
  top_k: 30
  num_beams: 3
  ...
```

## 🌐 API 端点总览

| 端点 | 方法 | 说明 | 兼容性 |
|------|------|------|--------|
| `/api/v1/health` | GET | 健康检查 | GLM-TTS 兼容 |
| `/api/v1/tts` | POST | 基础 TTS 生成 | GLM-TTS 兼容 |
| `/api/v1/tts/emotion` | POST | 情感控制 TTS | IndexTTS 特有 |
| `/api/v1/tts/advanced` | POST | 高级参数控制 | IndexTTS 特有 |
| `/api/v1/prompts` | GET | 索引列表 | IndexTTS 特有 |
| `/api/v1/stats/concurrency` | GET | 并发统计 | GLM-TTS 兼容 |

详细使用说明请参考：[INDEXTTS_API_CLIENT_GUIDE.md](docs/INDEXTTS_API_CLIENT_GUIDE.md)

## 🎤 音色索引速查

### 中文音色（8 个）

**女声**:
- `zh_female_gossip` - 八卦博主
- `zh_female_morning` - 晨间主播
- `zh_female_intellectual` - 知性风格
- `zh_female_investigative` - 调查记者

**男声**:
- `zh_male_sports` - 体育解说
- `zh_male_tech` - 科技UP主
- `zh_male_breaking_news` - 突发新闻
- `zh_male_talk_show` - 轻松脱口秀

### 英文音色（8 个）

**Female**:
- `en_female_gossip` - Gossip blogger
- `en_female_morning` - Morning anchor
- `en_female_intellectual` - Intellectual
- `en_female_investigative` - Investigative

**Male**:
- `en_male_sports` - Sports commentary
- `en_male_tech` - Tech geek
- `en_male_breaking_news` - Breaking news
- `en_male_talk_show` - Talk show

### 通用音色（12 个）

- `voice_01` ~ `voice_12` - 原有音色参考

### 情感参考（2 个）

- `emo_sad` - 悲伤情感
- `emo_hate` - 厌恶情感

## 🔧 服务管理（推荐使用管理脚本）

### 使用管理脚本

项目提供了 `api_server.sh` 管理脚本，可方便地管理 API 服务。

#### 启动服务

```bash
cd /data1/workspace/index-tts
./api_server.sh start
```

输出示例：
```
[INFO] Starting IndexTTS API Server...
[INFO] Working directory: /data1/workspace/index-tts
[INFO] Log file: /tmp/api_server.log
[INFO] Port: 8050
[INFO] ✓ API Server started successfully (PID: 123456)
[INFO] Waiting for model to load...
[INFO] ✓ Port 8050 is now listening
[INFO] ✓ Health check passed
[INFO] API Server is ready to accept requests
[INFO] API URL: http://localhost:8050
```

#### 停止服务（自动释放 GPU 显存）

```bash
./api_server.sh stop
```

输出示例：
```
[INFO] Stopping IndexTTS API Server...
[INFO] Stopping process (PID: 123456)...
[INFO] ✓ Process stopped gracefully
[INFO] Waiting for GPU memory release...
[INFO] ✓ GPU memory released
```

#### 查看服务状态

```bash
./api_server.sh status
```

输出示例：
```
===============================================
IndexTTS API Server Status
===============================================
Status:      RUNNING
PID:         123456
Port:        8050
CPU:         15.0%
Memory:      5.4%
Uptime:      00:36
Port Status: LISTENING
Model:       v2.0
Device:      cuda:0
FP16:        true
Prompts:     28
GPU Memory:  6704 MB
Log file:    /tmp/api_server.log
API URL:     http://localhost:8050
===============================================
```

#### 重启服务（自动释放 GPU 后重启）

```bash
./api_server.sh restart
```

### 手动命令（备选）

如果不使用管理脚本，也可以手动操作：

#### 启动服务

```bash
cd /data1/workspace/index-tts
export HF_ENDPOINT="https://hf-mirror.com"
nohup /data1/miniconda3/envs/xsmartvoice_env/bin/python api_server.py \
  --fp16 --api_port 8050 > /tmp/api_server.log 2>&1 &
```

#### 停止服务

```bash
pkill -f "api_server.py"
sleep 3  # 等待 GPU 显存释放
```

#### 查看日志

```bash
tail -f /tmp/api_server.log
```

#### 检查端口

```bash
netstat -tlnp | grep 8050
# 或
ss -tlnp | grep 8050
```

## 💾 显存使用

基于 NVIDIA L20 (46GB) 的实际使用情况：

| 服务 | 显存占用 | 端口 |
|------|---------|------|
| WebUI (webui.py) | ~6.7 GB | 7865 |
| API Server (api_server.py) | ~7.8 GB | 8050 |
| **总计** | **~14.5 GB** | - |

*使用 FP16 模式可节省约 40% 显存*

## ⚡ 性能优化建议

1. **启用 FP16**: 使用 `--fp16` 参数，加速 20-30%
2. **调整并发**: 根据 GPU 显存调整 `configs/api_config.yaml` 中的并发限制
3. **使用索引模式**: 避免上传文件，直接使用预置音色索引
4. **合理的 beam_size**: 
   - `beam_size=1`: 最快，质量略低
   - `beam_size=2-3`: 推荐，质量和速度平衡
   - `beam_size=4-5`: 最高质量，但速度慢

## 🐛 故障排除

### 服务无法启动

检查：
1. conda 环境是否激活
2. 模型文件是否完整（checkpoints 目录）
3. 端口是否被占用
4. GPU 显存是否充足

### 生成失败

检查：
1. 音色索引是否存在（使用 `/api/v1/prompts` 查询）
2. 文本是否为空
3. 并发是否超限（查看 `/api/v1/stats/concurrency`）
4. 服务日志（`/tmp/api_server.log`）

### 内存不足

解决方案：
1. 启用 FP16 模式
2. 降低并发限制
3. 减少 `max_mel_tokens` 参数

## 📖 更多文档

- [完整 API 使用指南](docs/INDEXTTS_API_CLIENT_GUIDE.md)
- [IndexTTS2 项目文档](README.md)
- [API 配置说明](configs/api_config.yaml)

---

**版本**: IndexTTS API v2.0  
**更新时间**: 2025-12-29

