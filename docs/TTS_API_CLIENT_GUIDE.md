# GLM-TTS API 客户端调用指南

本文档介绍如何在其他服务器或客户端应用中调用 GLM-TTS API 服务。

## 📋 目录

- [服务地址](#服务地址)
- [快速开始](#快速开始)
- [API 端点](#api-端点)
- [请求参数](#请求参数)
- [响应格式](#响应格式)
- [使用示例](#使用示例)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

## 🌐 服务地址

### 默认配置

- **服务地址**: `http://39.102.122.9:8049`
- **API 基础路径**: `/api/v1`
- **TTS 端点**: `POST /api/v1/tts`
- **健康检查**: `GET /api/v1/health`
- **并发统计**: `GET /api/v1/stats/concurrency`

### 确认服务可用

在调用 API 之前，建议先检查服务是否可用：

```bash
curl http://39.102.122.9:8049/api/v1/health
```

预期响应：
```json
{
    "status": "healthy",
    "model_loaded": true,
    "model_sample_rate": 24000,
    "model_use_phoneme": false,
    "prompt_cache_count": 2
}
```

## 🚀 快速开始

### Python 示例（最简单）

```python
import requests
import base64

# 服务地址
API_URL = "http://39.102.122.9:8049/api/v1/tts"

# 准备请求数据
data = {
    "input_text": "你好，这是一条测试消息。",
    "index": "exampleA",  # 使用预配置的提示音频
    "sample_rate": 24000,
    "use_cache": True,
    "use_phoneme": False,
    "sample_method": "ras",
    "sampling": 25,
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
        print(f"❌ 生成失败: {result['error']}")
else:
    print(f"❌ HTTP 错误: {response.status_code}")
```

### cURL 示例

```bash
curl -X POST http://39.102.122.9:8049/api/v1/tts \
  -F "input_text=你好，这是一条测试消息。" \
  -F "index=exampleA" \
  -F "sample_rate=24000" \
  -F "use_cache=true" \
  -F "use_phoneme=false" \
  -F "sample_method=ras" \
  -F "sampling=25" \
  -F "beam_size=1" \
  -o output.wav
```

## 📡 API 端点

### 1. 生成语音 (TTS)

**端点**: `POST /api/v1/tts`

**支持两种模式**：

#### 模式 1: 索引模式（推荐）

使用预配置的提示音频，通过 `index` 参数指定。

**优点**：
- 速度快（无需上传文件）
- 节省带宽
- 使用预优化的提示音频

#### 模式 2: 上传模式

上传自定义的提示音频文件。

**优点**：
- 灵活，可以使用任意音频
- 适合临时测试

## 📝 请求参数

### 必需参数

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `input_text` | string | 要合成的文本内容 | `"你好，世界"` |

### 可选参数

#### 提示音频配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `index` | string | `null` | 预配置的提示音频索引（如 `exampleA`） |
| `prompt_text` | string | `null` | 提示音频对应的文本（上传模式必需） |
| `prompt_audio` | file | `null` | 提示音频文件（上传模式必需） |

**注意**：`index` 和 `prompt_audio` 二选一，优先使用 `index`。

#### 生成参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `seed` | int | `42` | 随机种子，用于结果复现 |
| `sample_rate` | int | `24000` | 采样率，可选 `24000` 或 `32000` |
| `use_cache` | bool | `true` | 是否使用 KV 缓存（长文本推荐启用） |
| `use_phoneme` | bool | `false` | 是否启用音素控制（多音字处理） |
| `sample_method` | string | `"ras"` | 采样方法：`"ras"` 或 `"topk"` |
| `sampling` | int | `25` | 采样参数（Top-K），范围 1-100 |
| `beam_size` | int | `1` | 束搜索大小，范围 1-5 |

### 参数说明

#### `use_phoneme`（音素控制）

- **`false`**（推荐）：默认值，模型基于上下文判断多音字读音
- **`true`**：启用音素控制，适合生僻字、专业术语

**使用建议**：
- 包含大量多音字的文本 → 使用 `false`
- 包含生僻字的文本 → 可以尝试 `true`

#### `sample_rate`（采样率）

- **`24000`**：标准质量，处理速度快
- **`32000`**：高质量，处理时间稍长

#### `use_cache`（KV 缓存）

- **`true`**（推荐）：长文本生成更快，显存占用稍高
- **`false`**：显存占用低，但生成速度慢

#### `beam_size`（束搜索）

- **`1`**：不使用束搜索，速度最快
- **`2-3`**：推荐值，质量提升明显
- **`4-5`**：质量最高，但速度慢、显存占用高

## 📤 响应格式

### 成功响应

```json
{
    "success": true,
    "message": "Audio generated successfully",
    "audio_base64": "UklGRiQAAABXQVZFZm10...",
    "sample_rate": 24000,
    "generation_time": 3.45
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
    "error": "错误详情信息",
    "message": "Error message"
}
```

## 💻 使用示例

### Python 完整示例

```python
import requests
import base64
import time
from typing import Optional, Tuple

class GLMTTSClient:
    """GLM-TTS API 客户端"""
    
    def __init__(self, base_url: str = "http://39.102.122.9:8049"):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/v1/tts"
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
    
    def generate_tts(
        self,
        text: str,
        index: str = "exampleA",
        sample_rate: int = 24000,
        use_cache: bool = True,
        use_phoneme: bool = False,
        timeout: int = 600
    ) -> Tuple[bool, Optional[bytes], Optional[dict]]:
        """
        生成 TTS 音频
        
        Args:
            text: 要合成的文本
            index: 提示音频索引
            sample_rate: 采样率
            use_cache: 是否使用缓存
            use_phoneme: 是否启用音素控制
            timeout: 请求超时时间（秒）
        
        Returns:
            (success, audio_data, info)
        """
        # 准备请求数据
        data = {
            "input_text": text,
            "index": index,
            "sample_rate": sample_rate,
            "use_cache": "true" if use_cache else "false",
            "use_phoneme": "true" if use_phoneme else "false",
            "sample_method": "ras",
            "sampling": 25,
            "beam_size": 1
        }
        
        try:
            # 发送请求
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
                    # 解码音频数据
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
    
    def save_audio(self, audio_data: bytes, filename: str = "output.wav"):
        """保存音频文件"""
        with open(filename, "wb") as f:
            f.write(audio_data)
        print(f"✅ 音频已保存: {filename}")


# 使用示例
if __name__ == "__main__":
    # 创建客户端
    client = GLMTTSClient(base_url="http://39.102.122.9:8049")
    
    # 检查服务
    if not client.check_health():
        print("❌ 服务不可用，请检查服务地址和网络连接")
        exit(1)
    
    print("✅ 服务可用")
    
    # 生成语音
    text = "你好，这是一条测试消息。"
    success, audio_data, info = client.generate_tts(
        text=text,
        index="exampleA",
        use_phoneme=False
    )
    
    if success:
        print(f"✅ 生成成功！")
        print(f"⏱️  生成时间: {info['generation_time']:.2f} 秒")
        print(f"🎵 采样率: {info['sample_rate']} Hz")
        
        # 保存音频
        client.save_audio(audio_data, "output.wav")
    else:
        print(f"❌ 生成失败: {info.get('error')}")
```

### JavaScript/Node.js 示例

```javascript
const axios = require('axios');
const fs = require('fs');

class GLMTTSClient {
    constructor(baseUrl = 'http://39.102.122.9:8049') {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiUrl = `${this.baseUrl}/api/v1/tts`;
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
    
    async generateTTS(text, options = {}) {
        const {
            index = 'exampleA',
            sampleRate = 24000,
            useCache = true,
            usePhoneme = false,
            timeout = 600000
        } = options;
        
        const formData = new FormData();
        formData.append('input_text', text);
        formData.append('index', index);
        formData.append('sample_rate', sampleRate.toString());
        formData.append('use_cache', useCache.toString());
        formData.append('use_phoneme', usePhoneme.toString());
        formData.append('sample_method', 'ras');
        formData.append('sampling', '25');
        formData.append('beam_size', '1');
        
        try {
            const response = await axios.post(this.apiUrl, formData, {
                timeout,
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
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
    const client = new GLMTTSClient('http://39.102.122.9:8049');
    
    // 检查服务
    const isHealthy = await client.checkHealth();
    if (!isHealthy) {
        console.error('❌ 服务不可用');
        return;
    }
    
    console.log('✅ 服务可用');
    
    // 生成语音
    const result = await client.generateTTS('你好，这是一条测试消息。', {
        index: 'exampleA',
        usePhoneme: false
    });
    
    if (result.success) {
        console.log('✅ 生成成功！');
        console.log(`⏱️  生成时间: ${result.info.generationTime} 秒`);
        console.log(`🎵 采样率: ${result.info.sampleRate} Hz`);
        
        // 保存音频
        client.saveAudio(result.audio, 'output.wav');
    } else {
        console.error(`❌ 生成失败: ${result.error}`);
    }
}

main();
```

### Java 示例

```java
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Base64;

public class GLMTTSClient {
    private String baseUrl;
    
    public GLMTTSClient(String baseUrl) {
        this.baseUrl = baseUrl.replaceAll("/$", "");
    }
    
    public boolean checkHealth() {
        try {
            URL url = new URL(baseUrl + "/api/v1/health");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(5000);
            
            int responseCode = conn.getResponseCode();
            return responseCode == 200;
        } catch (Exception e) {
            System.err.println("健康检查失败: " + e.getMessage());
            return false;
        }
    }
    
    public byte[] generateTTS(String text, String index) throws Exception {
        String boundary = "----WebKitFormBoundary" + System.currentTimeMillis();
        URL url = new URL(baseUrl + "/api/v1/tts");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
        conn.setConnectTimeout(5000);
        conn.setReadTimeout(600000);
        
        try (OutputStream os = conn.getOutputStream();
             PrintWriter writer = new PrintWriter(new OutputStreamWriter(os, "UTF-8"), true)) {
            
            // 添加表单字段
            writer.append("--" + boundary).append("\r\n");
            writer.append("Content-Disposition: form-data; name=\"input_text\"").append("\r\n");
            writer.append("\r\n");
            writer.append(text).append("\r\n");
            
            writer.append("--" + boundary).append("\r\n");
            writer.append("Content-Disposition: form-data; name=\"index\"").append("\r\n");
            writer.append("\r\n");
            writer.append(index).append("\r\n");
            
            writer.append("--" + boundary).append("\r\n");
            writer.append("Content-Disposition: form-data; name=\"sample_rate\"").append("\r\n");
            writer.append("\r\n");
            writer.append("24000").append("\r\n");
            
            writer.append("--" + boundary).append("\r\n");
            writer.append("Content-Disposition: form-data; name=\"use_cache\"").append("\r\n");
            writer.append("\r\n");
            writer.append("true").append("\r\n");
            
            writer.append("--" + boundary).append("\r\n");
            writer.append("Content-Disposition: form-data; name=\"use_phoneme\"").append("\r\n");
            writer.append("\r\n");
            writer.append("false").append("\r\n");
            
            writer.append("--" + boundary).append("--").append("\r\n");
        }
        
        int responseCode = conn.getResponseCode();
        if (responseCode == 200) {
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream()))) {
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                
                // 解析 JSON（需要 JSON 库，这里简化处理）
                // 实际使用时建议使用 Gson 或 Jackson
                String jsonResponse = response.toString();
                if (jsonResponse.contains("\"success\":true")) {
                    // 提取 audio_base64
                    int start = jsonResponse.indexOf("\"audio_base64\":\"") + 16;
                    int end = jsonResponse.indexOf("\"", start);
                    String audioBase64 = jsonResponse.substring(start, end);
                    
                    return Base64.getDecoder().decode(audioBase64);
                } else {
                    throw new Exception("生成失败");
                }
            }
        } else {
            throw new Exception("HTTP 错误: " + responseCode);
        }
    }
    
    public void saveAudio(byte[] audioData, String filename) throws IOException {
        Files.write(Paths.get(filename), audioData);
        System.out.println("✅ 音频已保存: " + filename);
    }
    
    public static void main(String[] args) {
        GLMTTSClient client = new GLMTTSClient("http://39.102.122.9:8049");
        
        if (!client.checkHealth()) {
            System.err.println("❌ 服务不可用");
            return;
        }
        
        System.out.println("✅ 服务可用");
        
        try {
            byte[] audio = client.generateTTS("你好，这是一条测试消息。", "exampleA");
            client.saveAudio(audio, "output.wav");
            System.out.println("✅ 生成成功！");
        } catch (Exception e) {
            System.err.println("❌ 生成失败: " + e.getMessage());
        }
    }
}
```

## ⚠️ 错误处理

### 常见错误码

| HTTP 状态码 | 说明 | 解决方案 |
|------------|------|---------|
| `200` | 成功 | - |
| `400` | 请求参数错误 | 检查参数格式和取值范围 |
| `404` | 端点不存在 | 检查 API 路径是否正确 |
| `408` | 请求超时 | 增加超时时间，或减少文本长度 |
| `500` | 服务器内部错误 | 检查服务器日志 |

### 错误处理示例

```python
import requests
from requests.exceptions import Timeout, RequestException

def safe_generate_tts(text, max_retries=3):
    """带重试和错误处理的 TTS 生成"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://39.102.122.9:8049/api/v1/tts",
                data={
                    "input_text": text,
                    "index": "exampleA"
                },
                timeout=600
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return True, result
                else:
                    error = result.get("error", "Unknown error")
                    print(f"生成失败: {error}")
                    return False, error
            elif response.status_code == 408:
                print(f"请求超时（尝试 {attempt + 1}/{max_retries}）")
                if attempt < max_retries - 1:
                    continue
                return False, "Request timeout"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Timeout:
            print(f"连接超时（尝试 {attempt + 1}/{max_retries}）")
            if attempt < max_retries - 1:
                continue
            return False, "Connection timeout"
        except RequestException as e:
            print(f"请求异常: {e}")
            return False, str(e)
    
    return False, "Max retries exceeded"
```

## 🎯 最佳实践

### 1. 超时设置

根据文本长度设置合理的超时时间：

```python
def get_timeout(text_length):
    """根据文本长度计算超时时间"""
    if text_length <= 50:
        return 60  # 短文本：60 秒
    elif text_length <= 200:
        return 300  # 中等文本：5 分钟
    else:
        return 600  # 长文本：10 分钟

timeout = get_timeout(len(text))
```

### 2. 文本长度建议

- **短文本**（< 100 字）：处理速度快，推荐使用
- **中等文本**（100-500 字）：处理时间适中
- **长文本**（> 500 字）：
  - 建议启用 `use_cache=true`
  - 设置较长的超时时间（建议 5-10 分钟）
  - 考虑分段处理

### 3. 并发控制

如果需要进行并发请求，建议：

```python
import asyncio
import aiohttp

async def generate_tts_async(session, text, index="exampleA"):
    """异步生成 TTS"""
    data = aiohttp.FormData()
    data.add_field('input_text', text)
    data.add_field('index', index)
    data.add_field('sample_rate', '24000')
    data.add_field('use_cache', 'true')
    data.add_field('use_phoneme', 'false')
    
    async with session.post(
        'http://39.102.122.9:8049/api/v1/tts',
        data=data,
        timeout=aiohttp.ClientTimeout(total=600)
    ) as response:
        result = await response.json()
        if result.get('success'):
            return base64.b64decode(result['audio_base64'])
        else:
            raise Exception(result.get('error'))

# 并发调用示例
async def batch_generate(texts):
    async with aiohttp.ClientSession() as session:
        tasks = [generate_tts_async(session, text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
```

### 4. 音频格式处理

返回的音频是 WAV 格式，如果需要其他格式，可以转换：

```python
from pydub import AudioSegment

# 转换为 MP3
audio = AudioSegment.from_wav("output.wav")
audio.export("output.mp3", format="mp3")

# 转换为其他格式
audio.export("output.ogg", format="ogg")
audio.export("output.m4a", format="m4a")
```

### 5. 性能优化

- **使用索引模式**：避免重复上传提示音频
- **启用缓存**：长文本启用 `use_cache=true`
- **合理设置超时**：根据文本长度动态调整
- **批量处理**：使用异步请求提高效率

## ❓ 常见问题

### Q1: 如何获取可用的 `index` 列表？

A: 目前需要查看服务器端的 `configs/prompt_cache.json` 文件，或联系服务管理员。

### Q2: 支持哪些音频格式？

A: 目前只支持 WAV 格式输出。如需其他格式，可以在客户端进行转换。

### Q3: 如何处理长文本？

A: 建议：
1. 启用 `use_cache=true`
2. 设置较长的超时时间（600 秒以上）
3. 考虑分段处理，然后合并音频

### Q4: 并发请求有限制吗？

A: 是的，服务器端有并发限制：
- 短文本（≤200 字符）：默认 10 个并发
- 长文本（>200 字符）：默认 3 个并发

可以通过 `/api/v1/stats/concurrency` 端点查看当前并发状态。

### Q5: 如何提高生成质量？

A: 可以尝试：
- 增加 `beam_size`（2-3 推荐）
- 调整 `sampling` 参数（20-30 推荐）
- 使用 `sample_rate=32000`（高质量）

### Q6: 请求失败怎么办？

A: 检查：
1. 服务是否正常运行（健康检查）
2. 网络连接是否正常
3. 参数是否正确
4. 超时时间是否足够
5. 查看服务器日志

## 📚 相关文档

- [API 完整文档](API_DOCUMENTATION.md)
- [服务管理指南](API_SERVICE_MANAGEMENT.md)
- [Phoneme 功能说明](PHONEME_FEATURE_EXPLANATION.md)

## 🔗 联系支持

如有问题或建议，请联系服务管理员或查看项目文档。

