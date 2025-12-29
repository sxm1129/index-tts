"""
IndexTTS API Handler
Handles TTS generation requests with concurrency control and caching
"""

import asyncio
import base64
import json
import os
import time
import threading
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

import torch
import torchaudio
import numpy as np
from omegaconf import OmegaConf

from indextts.infer_v2 import IndexTTS2


class PromptCache:
    """Cache for audio prompt features"""
    
    def __init__(self, max_size: int = 50):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_order: List[str] = []
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached item"""
        with self.lock:
            if key in self.cache:
                # Update access order (LRU)
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
            return None
    
    def put(self, key: str, value: Any):
        """Put item into cache"""
        with self.lock:
            # Remove oldest if cache is full
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest = self.access_order.pop(0)
                del self.cache[oldest]
            
            # Add or update cache
            if key in self.cache:
                self.access_order.remove(key)
            self.cache[key] = value
            self.access_order.append(key)
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)


class ConcurrencyController:
    """Control concurrent TTS requests based on text length"""
    
    def __init__(self, max_short: int = 3, max_medium: int = 2, max_long: int = 1):
        self.semaphore_short = asyncio.Semaphore(max_short)
        self.semaphore_medium = asyncio.Semaphore(max_medium)
        self.semaphore_long = asyncio.Semaphore(max_long)
        self.current_tasks = 0
        self.total_requests = 0
        self.lock = threading.Lock()
    
    def get_semaphore(self, text_length: int) -> asyncio.Semaphore:
        """Get appropriate semaphore based on text length"""
        if text_length <= 100:
            return self.semaphore_short
        elif text_length <= 300:
            return self.semaphore_medium
        else:
            return self.semaphore_long
    
    def increment_task(self):
        """Increment current task count"""
        with self.lock:
            self.current_tasks += 1
            self.total_requests += 1
    
    def decrement_task(self):
        """Decrement current task count"""
        with self.lock:
            self.current_tasks = max(0, self.current_tasks - 1)
    
    def get_stats(self) -> Dict[str, int]:
        """Get concurrency statistics"""
        return {
            "current_tasks": self.current_tasks,
            "total_requests": self.total_requests,
            "max_concurrent_short": self.semaphore_short._value,
            "max_concurrent_medium": self.semaphore_medium._value,
            "max_concurrent_long": self.semaphore_long._value
        }


class ParameterConverter:
    """Convert GLM-TTS style parameters to IndexTTS2 parameters"""
    
    @staticmethod
    def convert_glm_to_indextts(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert GLM-TTS parameters to IndexTTS2 parameters
        
        Args:
            params: GLM-TTS style parameters
            
        Returns:
            IndexTTS2 compatible parameters
        """
        result = {}
        
        # Sample method conversion
        sample_method = params.get("sample_method", "ras").lower()
        if sample_method == "ras":
            result["do_sample"] = True
        elif sample_method == "topk":
            result["do_sample"] = True
            result["top_k"] = params.get("sampling", 25)
        
        # Beam size
        if "beam_size" in params:
            result["num_beams"] = params["beam_size"]
        
        # Sampling parameter
        if "sampling" in params and sample_method != "topk":
            result["top_k"] = params["sampling"]
        
        # Other generation parameters with defaults
        result["temperature"] = params.get("temperature", 0.8)
        result["top_p"] = params.get("top_p", 0.8)
        result["repetition_penalty"] = params.get("repetition_penalty", 10.0)
        result["length_penalty"] = params.get("length_penalty", 0.0)
        result["max_mel_tokens"] = params.get("max_mel_tokens", 1500)
        
        return result


class IndexTTSAPIHandler:
    """Main API handler for IndexTTS service"""
    
    def __init__(self, config_path: str = "configs/api_config.yaml",
                 prompt_cache_path: str = "configs/prompt_cache.json"):
        """
        Initialize API handler
        
        Args:
            config_path: Path to API configuration file
            prompt_cache_path: Path to prompt cache configuration
        """
        # Load configurations
        self.config = OmegaConf.load(config_path)
        with open(prompt_cache_path, 'r', encoding='utf-8') as f:
            self.prompt_config = json.load(f)
        
        # Initialize TTS model
        print(f"[API] Initializing IndexTTS2 model...")
        print(f"[API] Model dir: {self.config.model.model_dir}")
        print(f"[API] Config path: {self.config.model.config_path}")
        print(f"[API] FP16: {self.config.model.use_fp16}")
        print(f"[API] Device: {self.config.model.device}")
        
        self.tts = IndexTTS2(
            cfg_path=self.config.model.config_path,
            model_dir=self.config.model.model_dir,
            use_fp16=self.config.model.use_fp16,
            use_deepspeed=self.config.model.use_deepspeed,
            use_cuda_kernel=self.config.model.use_cuda_kernel,
            device=None if self.config.model.device == "auto" else self.config.model.device
        )
        
        print(f"[API] Model loaded successfully on device: {self.tts.device}")
        
        # Initialize components
        self.prompt_cache = PromptCache(max_size=self.config.cache.max_cached_prompts)
        self.concurrency = ConcurrencyController(
            max_short=self.config.concurrency.max_concurrent_short,
            max_medium=self.config.concurrency.max_concurrent_medium,
            max_long=self.config.concurrency.max_concurrent_long
        )
        self.converter = ParameterConverter()
        
        # Preload prompts if enabled
        if self.config.cache.enable_prompt_cache and self.config.cache.preload_all_prompts:
            self._preload_prompts()
        
        print(f"[API] API Handler initialized successfully")
        print(f"[API] Available prompts: {len(self.prompt_config['prompts'])}")
        print(f"[API] Available emotions: {len(self.prompt_config['emotions'])}")
    
    def _preload_prompts(self):
        """Preload all indexed prompts into cache"""
        print("[API] Preloading prompt features...")
        # Note: Feature extraction would happen here in production
        # For now, we just validate files exist
        for idx, info in self.prompt_config['prompts'].items():
            file_path = info['path']
            if os.path.exists(file_path):
                print(f"[API]   ✓ {idx}: {file_path}")
            else:
                print(f"[API]   ✗ {idx}: {file_path} NOT FOUND")
        print("[API] Preload complete")
    
    def get_prompt_path(self, index: str) -> Optional[str]:
        """Get prompt audio file path from index"""
        if index in self.prompt_config['prompts']:
            return self.prompt_config['prompts'][index]['path']
        return None
    
    def get_emotion_path(self, emo_index: str) -> Optional[str]:
        """Get emotion audio file path from index"""
        if emo_index in self.prompt_config['emotions']:
            return self.prompt_config['emotions'][emo_index]['path']
        return None
    
    def list_prompts(self) -> Dict[str, Any]:
        """List all available prompts"""
        return {
            "prompts": self.prompt_config['prompts'],
            "emotions": self.prompt_config['emotions']
        }
    
    async def generate_speech(
        self,
        text: str,
        prompt_path: str,
        output_path: Optional[str] = None,
        emo_audio_path: Optional[str] = None,
        emo_alpha: float = 1.0,
        emo_vector: Optional[List[float]] = None,
        use_emo_text: bool = False,
        emo_text: Optional[str] = None,
        use_random: bool = False,
        verbose: bool = False,
        **generation_kwargs
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Generate speech from text
        
        Args:
            text: Input text to synthesize
            prompt_path: Path to speaker prompt audio
            output_path: Output file path (if None, returns audio data)
            emo_audio_path: Path to emotion reference audio
            emo_alpha: Emotion weight (0.0-1.0)
            emo_vector: 8-dimensional emotion vector
            use_emo_text: Whether to use text-based emotion control
            emo_text: Emotion description text
            use_random: Whether to use random emotion sampling
            verbose: Whether to print verbose logs
            **generation_kwargs: Additional generation parameters
            
        Returns:
            (success, output_path_or_audio, info_dict)
        """
        try:
            text_length = len(text)
            semaphore = self.concurrency.get_semaphore(text_length)
            
            async with semaphore:
                self.concurrency.increment_task()
                
                try:
                    start_time = time.time()
                    
                    # Run inference in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        self._sync_generate,
                        text, prompt_path, output_path,
                        emo_audio_path, emo_alpha, emo_vector,
                        use_emo_text, emo_text, use_random,
                        verbose, generation_kwargs
                    )
                    
                    generation_time = time.time() - start_time
                    
                    info = {
                        "generation_time": generation_time,
                        "text_length": text_length,
                        "sample_rate": 24000
                    }
                    
                    return True, result, info
                    
                finally:
                    self.concurrency.decrement_task()
                    
        except Exception as e:
            print(f"[API ERROR] Generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False, None, {"error": str(e)}
    
    def _sync_generate(
        self,
        text: str,
        prompt_path: str,
        output_path: Optional[str],
        emo_audio_path: Optional[str],
        emo_alpha: float,
        emo_vector: Optional[List[float]],
        use_emo_text: bool,
        emo_text: Optional[str],
        use_random: bool,
        verbose: bool,
        generation_kwargs: Dict[str, Any]
    ) -> str:
        """Synchronous generation function (runs in thread pool)"""
        return self.tts.infer(
            spk_audio_prompt=prompt_path,
            text=text,
            output_path=output_path,
            emo_audio_prompt=emo_audio_path,
            emo_alpha=emo_alpha,
            emo_vector=emo_vector,
            use_emo_text=use_emo_text,
            emo_text=emo_text,
            use_random=use_random,
            verbose=verbose,
            **generation_kwargs
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        model_ver = getattr(self.tts, 'model_version', '2.0')
        if not isinstance(model_ver, str):
            model_ver = str(model_ver)
        
        return {
            "status": "healthy",
            "model_loaded": True,
            "model_version": model_ver,
            "device": str(self.tts.device),
            "fp16_enabled": self.tts.use_fp16,
            "available_prompts": len(self.prompt_config['prompts']),
            "available_emotions": len(self.prompt_config['emotions']),
            "cache_size": self.prompt_cache.size()
        }
    
    def get_concurrency_stats(self) -> Dict[str, Any]:
        """Get concurrency statistics"""
        return self.concurrency.get_stats()
    
    def clear_cache(self):
        """Clear prompt cache"""
        self.prompt_cache.clear()


def audio_to_base64(audio_path: str) -> str:
    """Convert audio file to base64 string"""
    with open(audio_path, 'rb') as f:
        audio_bytes = f.read()
    return base64.b64encode(audio_bytes).decode('utf-8')


def save_uploaded_audio(audio_data: bytes, filename: str = None) -> str:
    """Save uploaded audio to temporary file"""
    import tempfile
    if filename is None:
        fd, temp_path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
    else:
        temp_path = os.path.join(tempfile.gettempdir(), filename)
    
    with open(temp_path, 'wb') as f:
        f.write(audio_data)
    
    return temp_path

