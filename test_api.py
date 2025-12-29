#!/usr/bin/env python3
"""
IndexTTS API 测试脚本
演示如何调用 IndexTTS API 服务
"""

import requests
import base64
import sys
import json

API_BASE_URL = "http://localhost:8050"

def test_health():
    """测试健康检查端点"""
    print("=" * 60)
    print("测试 1: 健康检查")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health", timeout=5)
        result = response.json()
        
        print(f"✓ 服务状态: {result['status']}")
        print(f"  模型版本: {result['model_version']}")
        print(f"  设备: {result['device']}")
        print(f"  FP16: {result['fp16_enabled']}")
        print(f"  可用音色: {result['available_prompts']}")
        print(f"  可用情感: {result['available_emotions']}")
        return True
    except Exception as e:
        print(f"✗ 健康检查失败: {e}")
        return False

def test_basic_tts():
    """测试基础 TTS 生成"""
    print("\n" + "=" * 60)
    print("测试 2: 基础 TTS 生成（GLM-TTS 兼容）")
    print("=" * 60)
    
    data = {
        "input_text": "你好，欢迎使用IndexTTS语音合成服务。",
        "index": "zh_female_intellectual",
        "beam_size": 1
    }
    
    print(f"文本: {data['input_text']}")
    print(f"音色: {data['index']}")
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/tts", data=data, timeout=60)
        result = response.json()
        
        if result['success']:
            audio_data = base64.b64decode(result['audio_base64'])
            output_file = "test_basic.wav"
            
            with open(output_file, 'wb') as f:
                f.write(audio_data)
            
            print(f"✓ 生成成功")
            print(f"  生成时间: {result['generation_time']:.2f} 秒")
            print(f"  采样率: {result['sample_rate']} Hz")
            print(f"  音频大小: {len(audio_data)} bytes")
            print(f"  已保存: {output_file}")
            return True
        else:
            print(f"✗ 生成失败: {result.get('error')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_emotion_tts():
    """测试情感控制 TTS"""
    print("\n" + "=" * 60)
    print("测试 3: 情感控制 TTS（IndexTTS 特有）")
    print("=" * 60)
    
    data = {
        "input_text": "酒楼丧尽天良，开始借机竞拍房间，哎，一群蠢货。",
        "index": "zh_male_talk_show",
        "emo_index": "emo_sad",
        "emo_alpha": 0.65
    }
    
    print(f"文本: {data['input_text']}")
    print(f"音色: {data['index']}")
    print(f"情感: {data['emo_index']} (权重: {data['emo_alpha']})")
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/tts/emotion", data=data, timeout=60)
        result = response.json()
        
        if result['success']:
            audio_data = base64.b64decode(result['audio_base64'])
            output_file = "test_emotion.wav"
            
            with open(output_file, 'wb') as f:
                f.write(audio_data)
            
            print(f"✓ 生成成功")
            print(f"  生成时间: {result['generation_time']:.2f} 秒")
            print(f"  已保存: {output_file}")
            return True
        else:
            print(f"✗ 生成失败: {result.get('error')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_emotion_vector():
    """测试情感向量控制"""
    print("\n" + "=" * 60)
    print("测试 4: 情感向量控制")
    print("=" * 60)
    
    # [happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]
    emo_vector = [0, 0, 0, 0, 0, 0, 0.45, 0]  # surprised
    
    data = {
        "input_text": "哇塞！这个爆率也太高了！欧皇附体了！",
        "index": "voice_10",
        "emo_vector": json.dumps(emo_vector),
        "emo_alpha": 0.8
    }
    
    print(f"文本: {data['input_text']}")
    print(f"音色: {data['index']}")
    print(f"情感向量: {emo_vector} (惊喜)")
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/tts/emotion", data=data, timeout=60)
        result = response.json()
        
        if result['success']:
            audio_data = base64.b64decode(result['audio_base64'])
            output_file = "test_vector.wav"
            
            with open(output_file, 'wb') as f:
                f.write(audio_data)
            
            print(f"✓ 生成成功")
            print(f"  生成时间: {result['generation_time']:.2f} 秒")
            print(f"  已保存: {output_file}")
            return True
        else:
            print(f"✗ 生成失败: {result.get('error')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_list_prompts():
    """测试获取音色列表"""
    print("\n" + "=" * 60)
    print("测试 5: 获取可用音色列表")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/prompts", timeout=5)
        result = response.json()
        
        print(f"✓ 获取成功")
        print(f"\n中文女声音色:")
        for idx, info in result['prompts'].items():
            if info['language'] == 'zh' and info['gender'] == 'female':
                print(f"  - {idx}: {info['description']}")
        
        print(f"\n中文男声音色:")
        for idx, info in result['prompts'].items():
            if info['language'] == 'zh' and info['gender'] == 'male':
                print(f"  - {idx}: {info['description']}")
        
        print(f"\n英文音色: {sum(1 for i in result['prompts'].values() if i['language'] == 'en')} 个")
        print(f"通用音色: {sum(1 for i in result['prompts'].values() if i['language'] == 'mixed')} 个")
        print(f"情感参考: {len(result['emotions'])} 个")
        
        return True
    except Exception as e:
        print(f"✗ 获取失败: {e}")
        return False

def test_concurrency_stats():
    """测试并发统计"""
    print("\n" + "=" * 60)
    print("测试 6: 并发统计")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/stats/concurrency", timeout=5)
        result = response.json()
        
        print(f"✓ 获取成功")
        print(f"  当前任务数: {result['current_tasks']}")
        print(f"  总请求数: {result['total_requests']}")
        print(f"  短文本并发限制: {result['max_concurrent_short']}")
        print(f"  中等文本并发限制: {result['max_concurrent_medium']}")
        print(f"  长文本并发限制: {result['max_concurrent_long']}")
        
        return True
    except Exception as e:
        print(f"✗ 获取失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("IndexTTS API 测试脚本")
    print("=" * 60)
    print(f"API 地址: {API_BASE_URL}")
    print()
    
    tests = [
        ("健康检查", test_health),
        ("基础 TTS", test_basic_tts),
        ("情感控制", test_emotion_tts),
        ("情感向量", test_emotion_vector),
        ("音色列表", test_list_prompts),
        ("并发统计", test_concurrency_stats)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except KeyboardInterrupt:
            print("\n\n中断测试")
            sys.exit(1)
        except Exception as e:
            print(f"\n✗ 测试异常: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status}  {name}")
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 所有测试通过！")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())

