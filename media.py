import os
import time
import base64
import hmac
import hashlib
import requests
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

KLING_KEY      = os.getenv("KLING_API_KEY", "")
KLING_SECRET   = os.getenv("KLING_API_SECRET", "")
ELEVEN_KEY     = os.getenv("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE   = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")


# ── KLING AI ──────────────────────────────────────────────────────────────────

def get_kling_headers() -> dict:
    """Generate Kling API auth headers."""
    if not KLING_KEY or not KLING_SECRET:
        return {}
    timestamp  = str(int(time.time()))
    sign_str   = f"{KLING_KEY}{timestamp}"
    signature  = hmac.new(
        KLING_SECRET.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {KLING_KEY}",
        "X-Timestamp":   timestamp,
        "X-Signature":   signature,
    }


def generate_one_clip(prompt: str, duration: int = 6, scene_num: int = 1) -> str | None:
    """
    Generate one 6-second video clip with Kling AI.
    Returns video URL string or None on any failure.
    Never raises an exception — always returns gracefully.
    """
    print(f"  🎬 Scene {scene_num}: {prompt[:70]}...")

    if not KLING_KEY:
        print(f"  ⚠️  No KLING_API_KEY — skipping scene {scene_num}")
        return None

    try:
        headers = get_kling_headers()
        payload = {
            "model_name":      "kling-v1",
            "prompt":          prompt,
            "negative_prompt": "face, close up face, portrait, realistic photo, violence, disturbing, blur",
            "cfg_scale":       0.5,
            "mode":            "std",
            "duration":        str(duration),
            "aspect_ratio":    "16:9",
        }

        # Create generation task
        create = requests.post(
            "https://api.klingai.com/v1/videos/text2video",
            headers=headers,
            json=payload,
            timeout=30
        )

        if create.status_code != 200:
            print(f"  ❌ Scene {scene_num} create error: {create.status_code} — {create.text[:120]}")
            return None

        resp_data = create.json()
        task_id   = resp_data.get("data", {}).get("task_id")
        if not task_id:
            print(f"  ❌ Scene {scene_num}: no task_id returned")
            return None

        print(f"  ⏳ Scene {scene_num} task {task_id} — polling every 5s (max 120s)...")

        # Poll for completion
        for attempt in range(24):
            time.sleep(5)
            poll_headers = get_kling_headers()
            status = requests.get(
                f"https://api.klingai.com/v1/videos/text2video/{task_id}",
                headers=poll_headers,
                timeout=15
            )

            if status.status_code != 200:
                continue

            data       = status.json().get("data", {})
            task_status = data.get("task_status", "")

            if task_status == "succeed":
                videos = data.get("task_result", {}).get("videos", [])
                if videos:
                    url = videos[0].get("url", "")
                    print(f"  ✅ Scene {scene_num} done: {url[:80]}")
                    return url
                print(f"  ❌ Scene {scene_num}: success but no video URL")
                return None

            elif task_status == "failed":
                reason = data.get("task_status_msg", "unknown")
                print(f"  ❌ Scene {scene_num} failed: {reason}")
                return None

            print(f"     Scene {scene_num} attempt {attempt+1}/24 — {task_status}")

        print(f"  ❌ Scene {scene_num} timed out after 120s")
        return None

    except requests.exceptions.Timeout:
        print(f"  ❌ Scene {scene_num} request timed out")
        return None
    except Exception as e:
        print(f"  ❌ Scene {scene_num} exception: {e}")
        return None


# ── ELEVENLABS ────────────────────────────────────────────────────────────────

def voice_tone_to_settings(voice_tone: str) -> dict:
    """
    Map voice_tone description from Director brief to ElevenLabs settings.
    Returns voice_settings dict.
    """
    tone = voice_tone.lower()

    # Start with warm calm defaults
    stability       = 0.68
    similarity      = 0.80
    style           = 0.20
    speaker_boost   = True

    if any(w in tone for w in ["slow", "unhurried", "gentle", "soft"]):
        stability = 0.75
        style     = 0.15

    if any(w in tone for w in ["warm", "tender", "intimate"]):
        similarity = 0.85
        style      = 0.25

    if any(w in tone for w in ["quiet", "hushed", "whisper"]):
        stability  = 0.80
        similarity = 0.75

    if any(w in tone for w in ["melancholy", "heavy", "sorrowful"]):
        stability = 0.60
        style     = 0.35

    return {
        "stability":        stability,
        "similarity_boost": similarity,
        "style":            style,
        "use_speaker_boost": speaker_boost,
    }


def generate_audio(fable_text: str, voice_tone: str = "warm, quiet, unhurried") -> tuple:
    """
    Generate voice narration with ElevenLabs.
    Returns (audio_bytes, duration_ms) or (None, 35000) on failure.
    Never raises an exception.
    """
    print(f"\n🎙️  ElevenLabs generating audio...")
    print(f"   Voice tone: {voice_tone}")
    print(f"   Text length: {len(fable_text)} chars / ~{len(fable_text.split())} words")

    if not ELEVEN_KEY:
        print("  ⚠️  No ELEVENLABS_API_KEY — skipping audio")
        return None, 35000

    try:
        settings = voice_tone_to_settings(voice_tone)
        print(f"   ElevenLabs settings: {settings}")

        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE}",
            headers={
                "xi-api-key":    ELEVEN_KEY,
                "Content-Type":  "application/json",
                "Accept":        "audio/mpeg",
            },
            json={
                "text":       fable_text,
                "model_id":   "eleven_monolingual_v1",
                "voice_settings": settings,
            },
            timeout=30
        )

        if response.status_code == 200:
            audio_bytes = response.content
            # MP3 at ~128kbps = ~16000 bytes/sec
            duration_ms = max(int((len(audio_bytes) / 16000) * 1000), 5000)
            print(f"✅ Audio done — {len(audio_bytes):,} bytes — ~{duration_ms/1000:.1f}s")
            return audio_bytes, duration_ms

        print(f"❌ ElevenLabs error: {response.status_code} — {response.text[:150]}")
        return None, 35000

    except requests.exceptions.Timeout:
        print("❌ ElevenLabs timed out")
        return None, 35000
    except Exception as e:
        print(f"❌ ElevenLabs exception: {e}")
        return None, 35000


# ── PARALLEL MEDIA GENERATION ─────────────────────────────────────────────────

def generate_media_parallel(scenes: dict, fable_text: str, voice_tone: str) -> dict:
    """
    Run all 5 Kling video clips AND ElevenLabs audio simultaneously.
    Total wait = slowest single task (not sum of all tasks).
    Returns combined dict with video_urls list and audio data.
    """
    print(f"\n{'─'*50}")
    print(f"🚀 PARALLEL MEDIA GENERATION — 5 clips + 1 audio")
    print(f"{'─'*50}")

    video_urls  = [None] * 5
    audio_bytes = None
    duration_ms = 35000

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        # Submit all 5 video clips
        video_futures = {}
        for i in range(1, 6):
            key = f"scene_{i}"
            if key in scenes and scenes[key].get("prompt"):
                fut = executor.submit(
                    generate_one_clip,
                    scenes[key]["prompt"],
                    scenes[key].get("duration", 6),
                    i
                )
                video_futures[fut] = i - 1  # 0-indexed position

        # Submit audio
        audio_future = executor.submit(generate_audio, fable_text, voice_tone)

        # Collect video results as they complete
        for future in concurrent.futures.as_completed(video_futures):
            idx = video_futures[future]
            try:
                video_urls[idx] = future.result()
            except Exception as e:
                print(f"  ❌ Video future {idx+1} crashed: {e}")

        # Collect audio result
        try:
            audio_bytes, duration_ms = audio_future.result()
        except Exception as e:
            print(f"  ❌ Audio future crashed: {e}")

    # Summary
    successful = sum(1 for u in video_urls if u is not None)
    print(f"\n{'─'*50}")
    print(f"✅ MEDIA GENERATION COMPLETE")
    print(f"   Videos: {successful}/5 succeeded")
    print(f"   Audio:  {'✅ succeeded' if audio_bytes else '❌ failed — film will be silent'}")
    print(f"   Audio duration: {duration_ms/1000:.1f}s")
    print(f"{'─'*50}")

    return {
        "video_urls":       video_urls,
        "audio_b64":        base64.b64encode(audio_bytes).decode() if audio_bytes else None,
        "audio_duration_ms": duration_ms,
    }
