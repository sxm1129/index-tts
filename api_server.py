"""
IndexTTS API Server
FastAPI-based REST API service for IndexTTS2
Compatible with GLM-TTS API interface
"""

import argparse
import base64
import json
import logging
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Optional, List

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from indextts.api_handler import IndexTTSAPIHandler, audio_to_base64, save_uploaded_audio


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IndexTTS-API")


# Pydantic models for request/response validation
class TTSRequest(BaseModel):
    """TTS request model (for JSON requests)"""
    input_text: str = Field(..., description="Text to synthesize")
    index: Optional[str] = Field(None, description="Prompt audio index")
    sample_rate: int = Field(24000, description="Sample rate")
    use_cache: bool = Field(True, description="Use KV cache")
    use_phoneme: bool = Field(False, description="Use phoneme control")
    sample_method: str = Field("ras", description="Sampling method")
    sampling: int = Field(25, description="Sampling parameter (top-k)")
    beam_size: int = Field(1, description="Beam search size")


class TTSEmotionRequest(BaseModel):
    """TTS emotion control request model"""
    input_text: str = Field(..., description="Text to synthesize")
    index: str = Field(..., description="Speaker prompt audio index")
    emo_index: Optional[str] = Field(None, description="Emotion prompt audio index")
    emo_alpha: float = Field(1.0, ge=0.0, le=1.0, description="Emotion weight")
    emo_vector: Optional[List[float]] = Field(None, description="8-dim emotion vector")
    emo_text: Optional[str] = Field(None, description="Emotion description text")
    use_random: bool = Field(False, description="Use random emotion sampling")
    sample_rate: int = Field(24000, description="Sample rate")


class TTSResponse(BaseModel):
    """TTS response model"""
    success: bool
    message: str
    audio_base64: Optional[str] = None
    sample_rate: Optional[int] = None
    generation_time: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    model_version: str
    device: str
    fp16_enabled: bool
    available_prompts: int
    available_emotions: int


# Initialize FastAPI app
app = FastAPI(
    title="IndexTTS API",
    description="IndexTTS2 Text-to-Speech API Service",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Global handler instance
handler: Optional[IndexTTSAPIHandler] = None


# Middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} (took {process_time:.2f}s)")
    
    return response


@app.on_event("startup")
async def startup_event():
    """Initialize handler on startup"""
    global handler
    
    logger.info("=" * 80)
    logger.info("Starting IndexTTS API Server...")
    logger.info("=" * 80)
    
    try:
        handler = IndexTTSAPIHandler(
            config_path=args.config,
            prompt_cache_path=args.prompt_cache
        )
        logger.info("✓ API Handler initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize API Handler: {e}")
        traceback.print_exc()
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down IndexTTS API Server...")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns service status and model information
    """
    try:
        status = handler.get_health_status()
        return HealthResponse(**status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/prompts")
async def list_prompts():
    """
    List all available prompt audio indexes
    
    Returns dictionary of available prompts and emotions
    """
    try:
        return handler.list_prompts()
    except Exception as e:
        logger.error(f"List prompts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats/concurrency")
async def get_concurrency_stats():
    """
    Get concurrency statistics
    
    Returns current task count and total requests
    """
    try:
        return handler.get_concurrency_stats()
    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tts", response_model=TTSResponse)
async def generate_tts(
    input_text: str = Form(..., description="Text to synthesize"),
    index: Optional[str] = Form(None, description="Prompt audio index"),
    prompt_audio: Optional[UploadFile] = File(None, description="Prompt audio file"),
    prompt_text: Optional[str] = Form(None, description="Prompt text (for upload mode)"),
    sample_rate: int = Form(24000, description="Sample rate"),
    use_cache: str = Form("true", description="Use KV cache"),
    use_phoneme: str = Form("false", description="Use phoneme control"),
    sample_method: str = Form("ras", description="Sampling method"),
    sampling: int = Form(25, description="Top-K sampling"),
    beam_size: int = Form(1, description="Beam search size"),
    seed: int = Form(42, description="Random seed")
):
    """
    Basic TTS endpoint (GLM-TTS compatible)
    
    Supports two modes:
    - Index mode: Use 'index' parameter to specify pre-configured prompt
    - Upload mode: Upload 'prompt_audio' file
    """
    try:
        logger.info(f"[TTS] Request received - text length: {len(input_text)}, index: {index}")
        
        # Validate input
        if not input_text or len(input_text.strip()) == 0:
            return TTSResponse(
                success=False,
                message="Input text is empty",
                error="EMPTY_TEXT"
            )
        
        # Get prompt audio path
        prompt_path = None
        temp_files = []
        
        if index:
            # Index mode
            prompt_path = handler.get_prompt_path(index)
            if not prompt_path:
                return TTSResponse(
                    success=False,
                    message=f"Prompt index '{index}' not found",
                    error="INDEX_NOT_FOUND"
                )
            logger.info(f"[TTS] Using indexed prompt: {index} -> {prompt_path}")
        elif prompt_audio:
            # Upload mode
            audio_data = await prompt_audio.read()
            prompt_path = save_uploaded_audio(audio_data, f"prompt_{int(time.time())}.wav")
            temp_files.append(prompt_path)
            logger.info(f"[TTS] Using uploaded prompt: {prompt_path}")
        else:
            return TTSResponse(
                success=False,
                message="Either 'index' or 'prompt_audio' must be provided",
                error="MISSING_PROMPT"
            )
        
        # Convert GLM-TTS parameters to IndexTTS2 parameters
        gen_params = handler.converter.convert_glm_to_indextts({
            "sample_method": sample_method,
            "sampling": sampling,
            "beam_size": beam_size
        })
        
        logger.info(f"[TTS] Generation parameters: {gen_params}")
        
        # Generate output path
        output_path = os.path.join(tempfile.gettempdir(), f"output_{int(time.time())}.wav")
        temp_files.append(output_path)
        
        # Generate speech
        success, result, info = await handler.generate_speech(
            text=input_text,
            prompt_path=prompt_path,
            output_path=output_path,
            verbose=False,
            **gen_params
        )
        
        if success and result and os.path.exists(result):
            # Convert to base64
            audio_base64 = audio_to_base64(result)
            
            logger.info(f"[TTS] ✓ Generation successful - time: {info['generation_time']:.2f}s")
            
            # Cleanup temp files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
            
            return TTSResponse(
                success=True,
                message="Audio generated successfully",
                audio_base64=audio_base64,
                sample_rate=info.get('sample_rate', 24000),
                generation_time=info['generation_time']
            )
        else:
            # Cleanup temp files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
            
            error_msg = info.get('error', 'Unknown error') if info else 'Generation failed'
            logger.error(f"[TTS] ✗ Generation failed: {error_msg}")
            
            return TTSResponse(
                success=False,
                message="Generation failed",
                error=error_msg
            )
    
    except Exception as e:
        logger.error(f"[TTS] Exception: {e}")
        traceback.print_exc()
        return TTSResponse(
            success=False,
            message="Internal server error",
            error=str(e)
        )


@app.post("/api/v1/tts/emotion", response_model=TTSResponse)
async def generate_tts_emotion(
    input_text: str = Form(..., description="Text to synthesize"),
    index: str = Form(..., description="Speaker prompt audio index"),
    emo_index: Optional[str] = Form(None, description="Emotion prompt audio index"),
    emo_audio: Optional[UploadFile] = File(None, description="Emotion audio file"),
    emo_alpha: float = Form(1.0, ge=0.0, le=1.0, description="Emotion weight"),
    emo_vector: Optional[str] = Form(None, description="8-dim emotion vector as JSON array"),
    emo_text: Optional[str] = Form(None, description="Emotion description text"),
    use_random: str = Form("false", description="Use random emotion sampling"),
    sample_rate: int = Form(24000, description="Sample rate"),
    beam_size: int = Form(1, description="Beam search size")
):
    """
    Emotion-controlled TTS endpoint (IndexTTS specific)
    
    Supports multiple emotion control modes:
    - Use emo_index to specify emotion reference
    - Upload emo_audio for custom emotion
    - Use emo_vector for precise control
    - Use emo_text for text-based emotion
    """
    try:
        logger.info(f"[TTS-EMO] Request - text: {len(input_text)}chars, speaker: {index}, emo_index: {emo_index}")
        
        # Validate input
        if not input_text or len(input_text.strip()) == 0:
            return TTSResponse(
                success=False,
                message="Input text is empty",
                error="EMPTY_TEXT"
            )
        
        # Get speaker prompt path
        prompt_path = handler.get_prompt_path(index)
        if not prompt_path:
            return TTSResponse(
                success=False,
                message=f"Speaker prompt index '{index}' not found",
                error="INDEX_NOT_FOUND"
            )
        
        # Handle emotion reference
        emo_audio_path = None
        temp_files = []
        
        if emo_index:
            emo_audio_path = handler.get_emotion_path(emo_index)
            if not emo_audio_path:
                # Try as speaker prompt
                emo_audio_path = handler.get_prompt_path(emo_index)
            if not emo_audio_path:
                return TTSResponse(
                    success=False,
                    message=f"Emotion index '{emo_index}' not found",
                    error="EMO_INDEX_NOT_FOUND"
                )
            logger.info(f"[TTS-EMO] Using emotion index: {emo_index}")
        elif emo_audio:
            audio_data = await emo_audio.read()
            emo_audio_path = save_uploaded_audio(audio_data, f"emo_{int(time.time())}.wav")
            temp_files.append(emo_audio_path)
            logger.info(f"[TTS-EMO] Using uploaded emotion audio")
        
        # Parse emotion vector
        emo_vec = None
        if emo_vector:
            try:
                emo_vec = json.loads(emo_vector)
                if not isinstance(emo_vec, list) or len(emo_vec) != 8:
                    return TTSResponse(
                        success=False,
                        message="emo_vector must be an array of 8 floats",
                        error="INVALID_EMO_VECTOR"
                    )
                logger.info(f"[TTS-EMO] Using emotion vector: {emo_vec}")
            except json.JSONDecodeError:
                return TTSResponse(
                    success=False,
                    message="Invalid emo_vector JSON format",
                    error="INVALID_EMO_VECTOR_FORMAT"
                )
        
        # Parse use_random
        use_random_bool = use_random.lower() == "true"
        
        # Determine use_emo_text
        use_emo_text = emo_text is not None and len(emo_text.strip()) > 0
        
        # Generation parameters
        gen_params = handler.converter.convert_glm_to_indextts({
            "beam_size": beam_size
        })
        
        # Generate output path
        output_path = os.path.join(tempfile.gettempdir(), f"output_{int(time.time())}.wav")
        temp_files.append(output_path)
        
        # Generate speech
        success, result, info = await handler.generate_speech(
            text=input_text,
            prompt_path=prompt_path,
            output_path=output_path,
            emo_audio_path=emo_audio_path,
            emo_alpha=emo_alpha,
            emo_vector=emo_vec,
            use_emo_text=use_emo_text,
            emo_text=emo_text,
            use_random=use_random_bool,
            verbose=False,
            **gen_params
        )
        
        if success and result and os.path.exists(result):
            # Convert to base64
            audio_base64 = audio_to_base64(result)
            
            logger.info(f"[TTS-EMO] ✓ Success - time: {info['generation_time']:.2f}s")
            
            # Cleanup
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
            
            return TTSResponse(
                success=True,
                message="Audio generated successfully with emotion control",
                audio_base64=audio_base64,
                sample_rate=info.get('sample_rate', 24000),
                generation_time=info['generation_time']
            )
        else:
            # Cleanup
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
            
            error_msg = info.get('error', 'Unknown error') if info else 'Generation failed'
            logger.error(f"[TTS-EMO] ✗ Failed: {error_msg}")
            
            return TTSResponse(
                success=False,
                message="Generation failed",
                error=error_msg
            )
    
    except Exception as e:
        logger.error(f"[TTS-EMO] Exception: {e}")
        traceback.print_exc()
        return TTSResponse(
            success=False,
            message="Internal server error",
            error=str(e)
        )


@app.post("/api/v1/tts/advanced", response_model=TTSResponse)
async def generate_tts_advanced(
    input_text: str = Form(..., description="Text to synthesize"),
    index: str = Form(..., description="Speaker prompt audio index"),
    emo_index: Optional[str] = Form(None, description="Emotion prompt audio index"),
    emo_alpha: float = Form(1.0, description="Emotion weight"),
    emo_vector: Optional[str] = Form(None, description="8-dim emotion vector"),
    emo_text: Optional[str] = Form(None, description="Emotion description"),
    use_random: str = Form("false", description="Random emotion sampling"),
    # Advanced generation parameters
    do_sample: str = Form("true", description="Enable sampling"),
    temperature: float = Form(0.8, description="Temperature"),
    top_p: float = Form(0.8, description="Top-p"),
    top_k: int = Form(30, description="Top-k"),
    num_beams: int = Form(3, description="Beam size"),
    repetition_penalty: float = Form(10.0, description="Repetition penalty"),
    length_penalty: float = Form(0.0, description="Length penalty"),
    max_mel_tokens: int = Form(1500, description="Max mel tokens"),
    max_text_tokens_per_segment: int = Form(120, description="Max text tokens per segment")
):
    """
    Advanced TTS endpoint with full parameter control
    
    Exposes all IndexTTS2 generation parameters
    """
    try:
        logger.info(f"[TTS-ADV] Request - text: {len(input_text)}chars, index: {index}")
        
        # Validate input
        if not input_text or len(input_text.strip()) == 0:
            return TTSResponse(
                success=False,
                message="Input text is empty",
                error="EMPTY_TEXT"
            )
        
        # Get speaker prompt path
        prompt_path = handler.get_prompt_path(index)
        if not prompt_path:
            return TTSResponse(
                success=False,
                message=f"Speaker prompt index '{index}' not found",
                error="INDEX_NOT_FOUND"
            )
        
        # Handle emotion
        emo_audio_path = None
        if emo_index:
            emo_audio_path = handler.get_emotion_path(emo_index)
            if not emo_audio_path:
                emo_audio_path = handler.get_prompt_path(emo_index)
        
        # Parse emotion vector
        emo_vec = None
        if emo_vector:
            try:
                emo_vec = json.loads(emo_vector)
                if not isinstance(emo_vec, list) or len(emo_vec) != 8:
                    raise ValueError("Must be 8-element array")
            except:
                return TTSResponse(
                    success=False,
                    message="Invalid emo_vector format",
                    error="INVALID_EMO_VECTOR"
                )
        
        # Parse boolean parameters
        use_random_bool = use_random.lower() == "true"
        do_sample_bool = do_sample.lower() == "true"
        use_emo_text = emo_text is not None and len(emo_text.strip()) > 0
        
        # Generation parameters
        gen_params = {
            "do_sample": do_sample_bool,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k if top_k > 0 else None,
            "num_beams": num_beams,
            "repetition_penalty": repetition_penalty,
            "length_penalty": length_penalty,
            "max_mel_tokens": max_mel_tokens,
            "max_text_tokens_per_segment": max_text_tokens_per_segment
        }
        
        # Output path
        output_path = os.path.join(tempfile.gettempdir(), f"output_{int(time.time())}.wav")
        
        # Generate speech
        success, result, info = await handler.generate_speech(
            text=input_text,
            prompt_path=prompt_path,
            output_path=output_path,
            emo_audio_path=emo_audio_path,
            emo_alpha=emo_alpha,
            emo_vector=emo_vec,
            use_emo_text=use_emo_text,
            emo_text=emo_text,
            use_random=use_random_bool,
            verbose=False,
            **gen_params
        )
        
        if success and result and os.path.exists(result):
            audio_base64 = audio_to_base64(result)
            
            logger.info(f"[TTS-ADV] ✓ Success - time: {info['generation_time']:.2f}s")
            
            # Cleanup
            try:
                os.remove(output_path)
            except:
                pass
            
            return TTSResponse(
                success=True,
                message="Audio generated successfully",
                audio_base64=audio_base64,
                sample_rate=info.get('sample_rate', 24000),
                generation_time=info['generation_time']
            )
        else:
            error_msg = info.get('error', 'Unknown error') if info else 'Generation failed'
            logger.error(f"[TTS-ADV] ✗ Failed: {error_msg}")
            
            return TTSResponse(
                success=False,
                message="Generation failed",
                error=error_msg
            )
    
    except Exception as e:
        logger.error(f"[TTS-ADV] Exception: {e}")
        traceback.print_exc()
        return TTSResponse(
            success=False,
            message="Internal server error",
            error=str(e)
        )


@app.post("/api/v1/cache/clear")
async def clear_cache():
    """Clear prompt feature cache"""
    try:
        handler.clear_cache()
        logger.info("[CACHE] Cache cleared")
        return {"success": True, "message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"[CACHE] Clear failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IndexTTS API Server")
    parser.add_argument("--api_port", type=int, default=8049, help="API server port")
    parser.add_argument("--api_host", type=str, default="0.0.0.0", help="API server host")
    parser.add_argument("--config", type=str, default="configs/api_config.yaml", help="API config file")
    parser.add_argument("--prompt_cache", type=str, default="configs/prompt_cache.json", help="Prompt cache config")
    parser.add_argument("--model_dir", type=str, default=None, help="Model directory (overrides config)")
    parser.add_argument("--fp16", action="store_true", help="Enable FP16 (overrides config)")
    parser.add_argument("--device", type=str, default=None, help="Device (overrides config)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Run server
    logger.info(f"Starting server on {args.api_host}:{args.api_port}")
    uvicorn.run(
        app,
        host=args.api_host,
        port=args.api_port,
        reload=args.reload,
        log_level="info"
    )

