# IndexTTS API 客户端调用指南

本文档介绍如何在其他服务器或客户端应用中调用 IndexTTS API 服务。

## 📋 目录

- [服务地址](#服务地址)
- [快速开始](#快速开始)
- [API 端点](#api-端点)
- [请求参数](#请求参数)
- [响应格式](#响应格式)
- [音频索引列表](#音频索引列表)
- [使用示例](#使用示例)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

## 🌐 服务地址

### 默认配置

- **服务地址**: `http://39.102.122.9:8050`
- **API 基础路径**: `/api/v1`
- **基础 TTS 端点**: `POST /api/v1/tts` (兼容 GLM-TTS)
- **情感控制端点**: `POST /api/v1/tts/emotion` (IndexTTS 特有)
- **高级控制端点**: `POST /api/v1/tts/advanced` (IndexTTS 特有)
- **健康检查**: `GET /api/v1/health`
- **索引列表**: `GET /api/v1/prompts`
- **并发统计**: `GET /api/v1/stats/concurrency`

### 确认服务可用

在调用 API 之前，建议先检查服务是否可用：

```bash
curl http://39.102.122.9:8050/api/v1/health
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

## 🚀 快速开始

### Python 示例（最简单）

```python
import requests
import base64

# 服务地址
API_URL = "http://39.102.122.9:8050/api/v1/tts"

# 准备请求数据
data = {
    "input_text": "你好，这是一条测试消息。",
    "index": "zh_female_intellectual",  # 使用预配置的音色索引
    "beam_size": 1
}

# 发送请求
response = requests.post(API_URL, data=data, timeout=300)

# 处理响应
if response.status_code == 200:
    result = response.json()
    if result["success"]:
        # 解码音频数据
        audio_data = base64.b64decode(result["audio_base64"])
        
        # 保存音频文件
        with open("output.wav", "wb") as f:
            f.write(audio_data)
        
        print(f"✅ 生成成功！")
        print(f"⏱️  生成时间: {result['generation_time']} 秒")
        print(f"🎵 采样率: {result['sample_rate']} Hz")
    else:
        print(f"❌ 生成失败: {result.get('error')}")
else:
    print(f"❌ HTTP 错误: {response.status_code}")
```

### cURL 示例

```bash
curl -X POST http://39.102.122.9:8050/api/v1/tts \
  -F "input_text=你好，这是一条测试消息。" \
  -F "index=zh_female_intellectual" \
  -F "beam_size=1" \
  -o output.wav
```

## 📡 API 端点

### 1. 基础 TTS 生成 (GLM-TTS 兼容)

**端点**: `POST /api/v1/tts`

**支持两种模式**：

#### 模式 1: 索引模式（推荐）

使用预配置的音色索引，通过 `index` 参数指定。

**优点**：
- 速度快（无需上传文件）
- 节省带宽
- 使用优质的预置音色

**示例**：
```bash
curl -X POST http://39.102.122.9:8050/api/v1/tts \
  -F "input_text=欢迎使用IndexTTS。" \
  -F "index=zh_male_tech" \
  -F "beam_size=1"
```

#### 模式 2: 上传模式

上传自定义的音色参考音频文件。

**优点**：
- 灵活，可以使用任意音色
- 适合个性化需求

**示例**：
```bash
curl -X POST http://39.102.122.9:8050/api/v1/tts \
  -F "input_text=你好世界。" \
  -F "prompt_audio=@/path/to/your/voice.wav" \
  -F "beam_size=1"
```

### 2. 情感控制 TTS (IndexTTS 特有)

**端点**: `POST /api/v1/tts/emotion`

支持多种情感控制方式，是 IndexTTS2 的核心特色功能。

**情感控制模式**：

#### 模式 1: 情感参考音频索引
```bash
curl -X POST http://39.102.122.9:8050/api/v1/tts/emotion \
  -F "input_text=酒楼丧尽天良，开始借机竞拍房间，哎，一群蠢货。" \
  -F "index=zh_male_talk_show" \
  -F "emo_index=emo_sad" \
  -F "emo_alpha=0.65"
```

#### 模式 2: 8维情感向量
```bash
curl -X POST http://39.102.122.9:8050/api/v1/tts/emotion \
  -F "input_text=哇塞！这个爆率也太高了！" \
  -F "index=voice_10" \
  -F 'emo_vector=[0,0,0,0,0,0,0.45,0]' \
  -F "emo_alpha=0.8"
```

情感向量格式：`[happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]`

#### 模式 3: 文本描述情感（实验性）
```bash
curl -X POST http://39.102.122.9:8050/api/v1/tts/emotion \
  -F "input_text=快躲起来！是他要来了！" \
  -F "index=voice_12" \
  -F "emo_text=极度恐惧" \
  -F "emo_alpha=0.6"
```

### 3. 高级 TTS (完整参数控制)

**端点**: `POST /api/v1/tts/advanced`

暴露 IndexTTS2 的全部生成参数，适合高级用户精细调优。

```bash
curl -X POST http://39.102.122.9:8050/api/v1/tts/advanced \
  -F "input_text=这是一段测试文本。" \
  -F "index=zh_female_morning" \
  -F "do_sample=true" \
  -F "temperature=0.9" \
  -F "top_p=0.85" \
  -F "top_k=35" \
  -F "num_beams=3" \
  -F "repetition_penalty=10.0"
```

### 4. 获取音色索引列表

**端点**: `GET /api/v1/prompts`

返回所有可用的音色和情感索引。

```bash
curl http://39.102.122.9:8050/api/v1/prompts
```

### 5. 健康检查

**端点**: `GET /api/v1/health`

检查服务状态和模型信息。

```bash
curl http://39.102.122.9:8050/api/v1/health
```

### 6. 并发统计

**端点**: `GET /api/v1/stats/concurrency`

查看当前并发情况。

```bash
curl http://39.102.122.9:8050/api/v1/stats/concurrency
```

## 📝 请求参数

### 基础 TTS 端点参数

#### 必需参数

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `input_text` | string | 要合成的文本内容 | `"你好，世界"` |

#### 音色配置（二选一）

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `index` | string | `null` | 预配置的音色索引（推荐） |
| `prompt_audio` | file | `null` | 上传音色参考音频文件 |

#### 生成参数（可选）

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `sample_rate` | int | `24000` | 采样率 |
| `use_cache` | string | `"true"` | 是否使用缓存 |
| `use_phoneme` | string | `"false"` | 音素控制（暂不支持） |
| `sample_method` | string | `"ras"` | 采样方法 |
| `sampling` | int | `25` | Top-K 采样值 |
| `beam_size` | int | `1` | 束搜索大小 (1-5) |
| `seed` | int | `42` | 随机种子 |

### 情感控制端点参数

在基础参数之上，增加以下情感控制参数：

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `emo_index` | string | `null` | 情感参考音频索引 |
| `emo_audio` | file | `null` | 上传情感参考音频 |
| `emo_alpha` | float | `1.0` | 情感权重 (0.0-1.0) |
| `emo_vector` | string | `null` | JSON 格式的 8 维情感向量 |
| `emo_text` | string | `null` | 情感描述文本 |
| `use_random` | string | `"false"` | 是否使用随机采样 |

### 高级端点参数

完整的生成参数控制：

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `do_sample` | string | `"true"` | 是否启用采样 |
| `temperature` | float | `0.8` | 温度参数 (0.1-2.0) |
| `top_p` | float | `0.8` | Top-P 核采样 (0.0-1.0) |
| `top_k` | int | `30` | Top-K 采样 (0-100) |
| `num_beams` | int | `3` | 束搜索大小 (1-10) |
| `repetition_penalty` | float | `10.0` | 重复惩罚 |
| `length_penalty` | float | `0.0` | 长度惩罚 |
| `max_mel_tokens` | int | `1500` | 最大梅尔频谱 token 数 |
| `max_text_tokens_per_segment` | int | `120` | 每段最大文本 token 数 |

## 📤 响应格式

### 成功响应

```json
{
    "success": true,
    "message": "Audio generated successfully",
    "audio_base64": "UklGRiQAAABXQVZFZm10...",
    "sample_rate": 24000,
    "generation_time": 1.08
}
```

### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `success` | boolean | 是否成功 |
| `message` | string | 响应消息 |
| `audio_base64` | string | Base64 编码的音频数据（WAV 格式） |
| `sample_rate` | int | 音频采样率 |
| `generation_time` | float | 生成耗时（秒） |
| `error` | string | 错误信息（仅失败时） |

### 失败响应

```json
{
    "success": false,
    "message": "Generation failed",
    "error": "错误详情信息"
}
```

## 🎤 音频索引列表

### 中文音色

#### 女声

| 索引 | 描述 | 适用场景 |
|------|------|---------|
| `zh_female_gossip` | 活泼八卦风格 | 娱乐、八卦类内容 |
| `zh_female_morning` | 温和亲切的早间主播 | 新闻播报、晨间节目 |
| `zh_female_intellectual` | 专业稳重知性风格 | 知识性内容、教育 |
| `zh_female_investigative` | 严肃质询的调查记者 | 深度报道、访谈 |

#### 男声

| 索引 | 描述 | 适用场景 |
|------|------|---------|
| `zh_male_sports` | 激情快节奏体育解说 | 体育赛事解说 |
| `zh_male_tech` | 年轻活力的科技UP主 | 科技评测、教程 |
| `zh_male_breaking_news` | 紧急严肃的突发新闻 | 新闻快讯、重要通知 |
| `zh_male_talk_show` | 幽默轻松的脱口秀 | 娱乐节目、脱口秀 |

### 英文音色

#### 女声

| 索引 | 描述 | 适用场景 |
|------|------|---------|
| `en_female_gossip` | Lively gossip style | Entertainment, celebrity news |
| `en_female_morning` | Warm morning anchor | Morning news, broadcasts |
| `en_female_intellectual` | Professional commentary | Educational content |
| `en_female_investigative` | Serious investigative | In-depth reporting |

#### 男声

| 索引 | 描述 | 适用场景 |
|------|------|---------|
| `en_male_sports` | Energetic sports commentary | Sports broadcasting |
| `en_male_tech` | Tech geek enthusiast | Tech reviews, tutorials |
| `en_male_breaking_news` | Urgent news reporter | Breaking news, alerts |
| `en_male_talk_show` | Casual talk show host | Talk shows, entertainment |

### 通用音色

| 索引 | 描述 |
|------|------|
| `voice_01` ~ `voice_12` | 原有音色参考 01-12 |

### 情感索引

| 索引 | 描述 |
|------|------|
| `emo_sad` | 悲伤情感参考 |
| `emo_hate` | 厌恶情感参考 |

## 💻 使用示例

### Python 完整示例

```python
import requests
import base64
import time
from typing import Optional, Tuple

class IndexTTSClient:
    """IndexTTS API 客户端"""
    
    def __init__(self, base_url: str = "http://39.102.122.9:8050"):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/v1/tts"
        self.emotion_url = f"{self.base_url}/api/v1/tts/emotion"
        self.health_url = f"{self.base_url}/api/v1/health"
    
    def check_health(self) -> bool:
        """检查服务是否可用"""
        try:
            response = requests.get(self.health_url, timeout=5)
            if response.status_code == 200:
                result = response.json()
                return result.get("status") == "healthy"
        except Exception as e:
            print(f"健康检查失败: {e}")
        return False
    
    def generate_basic(
        self,
        text: str,
        index: str = "zh_female_intellectual",
        beam_size: int = 1,
        timeout: int = 600
    ) -> Tuple[bool, Optional[bytes], Optional[dict]]:
        """
        基础 TTS 生成（兼容 GLM-TTS）
        
        Args:
            text: 要合成的文本
            index: 音色索引
            beam_size: 束搜索大小
            timeout: 请求超时时间（秒）
        
        Returns:
            (success, audio_data, info)
        """
        data = {
            "input_text": text,
            "index": index,
            "beam_size": beam_size,
            "sample_rate": 24000
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                self.api_url,
                data=data,
                timeout=timeout
            )
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    audio_base64 = result.get("audio_base64")
                    if audio_base64:
                        audio_data = base64.b64decode(audio_base64)
                        info = {
                            "generation_time": result.get("generation_time"),
                            "sample_rate": result.get("sample_rate"),
                            "total_time": elapsed_time
                        }
                        return True, audio_data, info
                    else:
                        return False, None, {"error": "No audio data in response"}
                else:
                    return False, None, {"error": result.get("error", "Unknown error")}
            else:
                return False, None, {
                    "error": f"HTTP {response.status_code}",
                    "detail": response.text
                }
        except requests.exceptions.Timeout:
            return False, None, {"error": "Request timeout"}
        except Exception as e:
            return False, None, {"error": str(e)}
    
    def generate_with_emotion(
        self,
        text: str,
        index: str,
        emo_index: Optional[str] = None,
        emo_alpha: float = 1.0,
        emo_vector: Optional[list] = None,
        emo_text: Optional[str] = None,
        timeout: int = 600
    ) -> Tuple[bool, Optional[bytes], Optional[dict]]:
        """
        带情感控制的 TTS 生成
        
        Args:
            text: 要合成的文本
            index: 音色索引
            emo_index: 情感参考索引
            emo_alpha: 情感权重 (0.0-1.0)
            emo_vector: 8 维情感向量
            emo_text: 情感描述文本
            timeout: 请求超时时间
        
        Returns:
            (success, audio_data, info)
        """
        import json
        
        data = {
            "input_text": text,
            "index": index,
            "emo_alpha": emo_alpha
        }
        
        if emo_index:
            data["emo_index"] = emo_index
        if emo_vector:
            data["emo_vector"] = json.dumps(emo_vector)
        if emo_text:
            data["emo_text"] = emo_text
        
        try:
            response = requests.post(
                self.emotion_url,
                data=data,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    audio_data = base64.b64decode(result["audio_base64"])
                    info = {
                        "generation_time": result.get("generation_time"),
                        "sample_rate": result.get("sample_rate")
                    }
                    return True, audio_data, info
                else:
                    return False, None, {"error": result.get("error")}
            else:
                return False, None, {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return False, None, {"error": str(e)}
    
    def save_audio(self, audio_data: bytes, filename: str = "output.wav"):
        """保存音频文件"""
        with open(filename, "wb") as f:
            f.write(audio_data)
        print(f"✅ 音频已保存: {filename}")


# 使用示例
if __name__ == "__main__":
    # 创建客户端
    client = IndexTTSClient(base_url="http://39.102.122.9:8050")
    
    # 检查服务
    if not client.check_health():
        print("❌ 服务不可用")
        exit(1)
    
    print("✅ 服务可用")
    
    # 示例 1: 基础生成
    print("\n=== 基础 TTS 生成 ===")
    success, audio, info = client.generate_basic(
        text="你好，欢迎使用IndexTTS语音合成服务。",
        index="zh_female_intellectual"
    )
    
    if success:
        client.save_audio(audio, "output_basic.wav")
        print(f"⏱️  生成时间: {info['generation_time']:.2f} 秒")
    else:
        print(f"❌ 失败: {info.get('error')}")
    
    # 示例 2: 情感控制生成
    print("\n=== 情感控制 TTS 生成 ===")
    success, audio, info = client.generate_with_emotion(
        text="酒楼丧尽天良，开始借机竞拍房间，哎，一群蠢货。",
        index="zh_male_talk_show",
        emo_index="emo_sad",
        emo_alpha=0.65
    )
    
    if success:
        client.save_audio(audio, "output_emotion.wav")
        print(f"⏱️  生成时间: {info['generation_time']:.2f} 秒")
    else:
        print(f"❌ 失败: {info.get('error')}")
    
    # 示例 3: 情感向量控制
    print("\n=== 情感向量控制 ===")
    success, audio, info = client.generate_with_emotion(
        text="哇塞！这个爆率也太高了！",
        index="voice_10",
        emo_vector=[0, 0, 0, 0, 0, 0, 0.45, 0],  # surprised
        emo_alpha=0.8
    )
    
    if success:
        client.save_audio(audio, "output_vector.wav")
        print(f"⏱️  生成时间: {info['generation_time']:.2f} 秒")
    else:
        print(f"❌ 失败: {info.get('error')}")
```

### JavaScript/Node.js 示例

```javascript
const axios = require('axios');
const fs = require('fs');

class IndexTTSClient {
    constructor(baseUrl = 'http://39.102.122.9:8050') {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiUrl = `${this.baseUrl}/api/v1/tts`;
        this.emotionUrl = `${this.baseUrl}/api/v1/tts/emotion`;
    }
    
    async checkHealth() {
        try {
            const response = await axios.get(`${this.baseUrl}/api/v1/health`);
            return response.data.status === 'healthy';
        } catch (error) {
            console.error('健康检查失败:', error.message);
            return false;
        }
    }
    
    async generateBasic(text, index = 'zh_female_intellectual') {
        const FormData = require('form-data');
        const formData = new FormData();
        
        formData.append('input_text', text);
        formData.append('index', index);
        formData.append('beam_size', '1');
        
        try {
            const response = await axios.post(this.apiUrl, formData, {
                timeout: 600000,
                headers: formData.getHeaders()
            });
            
            if (response.data.success) {
                const audioBuffer = Buffer.from(
                    response.data.audio_base64,
                    'base64'
                );
                return {
                    success: true,
                    audio: audioBuffer,
                    info: {
                        generationTime: response.data.generation_time,
                        sampleRate: response.data.sample_rate
                    }
                };
            } else {
                return {
                    success: false,
                    error: response.data.error
                };
            }
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    saveAudio(audioBuffer, filename = 'output.wav') {
        fs.writeFileSync(filename, audioBuffer);
        console.log(`✅ 音频已保存: ${filename}`);
    }
}

// 使用示例
async function main() {
    const client = new IndexTTSClient('http://39.102.122.9:8050');
    
    if (!await client.checkHealth()) {
        console.error('❌ 服务不可用');
        return;
    }
    
    console.log('✅ 服务可用');
    
    const result = await client.generateBasic(
        '你好，欢迎使用IndexTTS。',
        'zh_female_morning'
    );
    
    if (result.success) {
        console.log('✅ 生成成功！');
        console.log(`⏱️  生成时间: ${result.info.generationTime} 秒`);
        client.saveAudio(result.audio, 'output.wav');
    } else {
        console.error(`❌ 失败: ${result.error}`);
    }
}

main();
```

## ⚠️ 错误处理

### 常见错误码

| HTTP 状态码 | 说明 | 解决方案 |
|------------|------|---------|
| `200` | 成功 | - |
| `400` | 请求参数错误 | 检查参数格式和取值范围 |
| `404` | 端点不存在 | 检查 API 路径是否正确 |
| `408` | 请求超时 | 增加超时时间，或减少文本长度 |
| `422` | 参数验证失败 | 检查参数类型和格式 |
| `500` | 服务器内部错误 | 检查服务器日志 |

### 业务错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|---------|
| `EMPTY_TEXT` | 输入文本为空 | 提供非空文本 |
| `INDEX_NOT_FOUND` | 音色索引不存在 | 使用 `/api/v1/prompts` 查看可用索引 |
| `EMO_INDEX_NOT_FOUND` | 情感索引不存在 | 检查情感索引是否正确 |
| `MISSING_PROMPT` | 缺少音色参数 | 提供 index 或 prompt_audio |
| `INVALID_EMO_VECTOR` | 情感向量格式错误 | 确保为 8 个浮点数的数组 |

## 🎯 最佳实践

### 1. 音色选择建议

根据内容类型选择合适的音色索引：

- **新闻播报**: `zh_female_morning`, `zh_male_breaking_news`
- **知识科普**: `zh_female_intellectual`, `zh_male_tech`
- **娱乐内容**: `zh_female_gossip`, `zh_male_talk_show`
- **体育解说**: `zh_male_sports`, `en_male_sports`
- **深度报道**: `zh_female_investigative`, `en_female_investigative`

### 2. 情感控制建议

- **情感强度**: 建议 `emo_alpha` 在 0.6-0.8 之间，过高可能影响音色还原度
- **文本情感**: 使用 `emo_text` 时，建议 `emo_alpha` 设为 0.6 或更低
- **随机采样**: `use_random=true` 会降低音色还原度，谨慎使用

### 3. 性能优化

- **短文本**: 优先使用索引模式，避免文件上传开销
- **并发控制**: 注意服务端并发限制（短文本 3 并发，长文本 1 并发）
- **超时设置**: 短文本 60 秒，中等文本 300 秒，长文本 600 秒

### 4. 文本长度建议

- **短文本** (< 50 字): 处理最快，推荐使用
- **中等文本** (50-200 字): 处理时间适中
- **长文本** (> 200 字): 处理时间较长，建议分段或增加超时

## ❓ 常见问题

### Q1: 如何从 GLM-TTS 迁移到 IndexTTS？

A: 只需修改 API 基础 URL，参数保持不变：

```python
# GLM-TTS
API_URL = "http://39.102.122.9:8049/api/v1/tts"

# IndexTTS（修改为您的服务地址）
API_URL = "http://39.102.122.9:8050/api/v1/tts"
```

### Q2: 支持哪些音频格式？

A: 
- **输入**: 支持 WAV, MP3 等常见格式
- **输出**: WAV 格式（24kHz，16-bit）

### Q3: 如何查看可用的音色索引？

A: 调用索引列表 API：

```bash
curl http://39.102.122.9:8050/api/v1/prompts
```

### Q4: 情感向量如何使用？

A: 8 维情感向量对应 8 种情感，取值范围 0.0-1.0：

```python
# [happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]
emo_vector = [0, 0, 0.8, 0, 0, 0, 0, 0]  # 悲伤情感
```

### Q5: 并发请求有限制吗？

A: 是的，服务器端有并发限制：
- 短文本（≤ 100 字符）: 最多 3 个并发
- 中等文本（101-300 字符）: 最多 2 个并发
- 长文本（> 300 字符）: 最多 1 个并发

可通过 `/api/v1/stats/concurrency` 查看当前状态。

### Q6: 生成时间大概多长？

A: 根据文本长度和硬件配置：
- 短文本（< 20 字）: 1-3 秒
- 中等文本（20-100 字）: 3-10 秒
- 长文本（> 100 字）: 10-30 秒

启用 FP16 可以加速约 20-30%。

### Q7: 如何提高生成质量？

A: 可以尝试：
- 增加 `beam_size` (2-3 推荐，质量提升明显)
- 调整 `temperature` (0.7-0.9，影响多样性)
- 使用情感控制增强表现力

### Q8: 支持流式输出吗？

A: 当前版本暂不支持流式输出，未来版本会考虑添加。

## 📚 相关文档

- [IndexTTS2 项目主页](https://github.com/index-tts/index-tts)
- [IndexTTS2 论文](https://arxiv.org/abs/2506.21619)
- [API 服务配置说明](../configs/api_config.yaml)

## 🔗 联系支持

- **QQ 群**: 663272642(No.4) 1013410623(No.5)
- **Discord**: https://discord.gg/uT32E7KDmy
- **Email**: indexspeech@bilibili.com

## 📊 性能参考

基于 NVIDIA L20 GPU (46GB) + FP16 模式的测试结果：

| 文本长度 | 生成时间 | 显存占用 |
|---------|---------|---------|
| 10 字 | ~1-2 秒 | ~5.3 GB |
| 50 字 | ~3-5 秒 | ~5.3 GB |
| 200 字 | ~10-15 秒 | ~5.3 GB |

*注意: 实际性能因硬件配置而异*

