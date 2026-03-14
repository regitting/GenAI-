# NarrativeCare AI — Cursor Context File
# Read this entire file before making any changes to the project.
# This file explains what every piece does, why it exists, and how it all connects.

# ══════════════════════════════════════════════════════════════════════════════
# WHAT THIS PROJECT IS
# ══════════════════════════════════════════════════════════════════════════════
#
# NarrativeCare AI is a mental wellness tool for organizations
# (universities, hospitals, companies).
#
# A person describes a stressful situation.
# Three AI agents reason about it and produce:
#   1. A 120-word fable narration (written to be read aloud)
#   2. Five 6-second video prompts (for Kling AI to generate)
#   3. Visual direction (color, lighting, movement for the film)
#
# Kling AI generates 5 video clips in parallel (~75 seconds).
# ElevenLabs generates voice narration in parallel.
# The frontend plays all 5 clips in sequence as a 30-second film
# with the fable narrated over it word by word.
#
# The insight the person needs is NEVER stated directly.
# It is embedded inside what happens to the character in the fable.
# The viewer feels it without being told it.
#
# ══════════════════════════════════════════════════════════════════════════════
# THE THREE AI AGENTS — what each one does
# ══════════════════════════════════════════════════════════════════════════════
#
# AGENT 1 — DIRECTOR (run_director function in pipeline.py)
#   Input:  raw user text ("I failed my midterm after studying for weeks")
#   Output: a rich JSON "brief" with 15+ fields
#
#   Step 0 — SAFETY (before creative work): If the person's words suggest serious
#   or immediate risk (self-harm, suicide, abuse, crisis), the Director sets
#   show_crisis_resources: true, severity: "crisis", and crisis_note. The API
#   always returns a resources object (988, Crisis Text Line, disclaimer) so the
#   frontend can direct people to proper help when needed. NarrativeCare takes
#   serious mental health seriously; it is not a substitute for professional care.
#
#   What it does internally (6 reasoning steps):
#   Step 1: Finds one specific word the user uses that reveals something
#   Step 2: Names the CONTRADICTION between what they say and what words reveal
#   Step 3: Maps 5 structural elements (effort/visibility/agency/people/time)
#           then invents a character whose situation has the SAME STRUCTURE
#   Step 4: Creates 5 filmable scene beats, each built around a physical object
#   Step 5: Identifies the insight — must pass 3 tests (recognition/resistance/specificity)
#   Step 6: Decides visual direction (color temp, lighting, movement, atmosphere)
#
#   Key principle: the character mirrors the STRUCTURE of the person's situation,
#   not just the feeling. This is what makes stories feel specifically true.
#
# AGENT 2 — WRITER (run_writer function in pipeline.py)
#   Input:  Director's brief JSON (NEVER sees the original user text)
#   Output: 120-word fable narration string
#
#   What it does:
#   - Writes in third person ("There was a...")
#   - Uses why_this_character to make the story structurally precise
#   - Uses character_detail to make the character feel real
#   - Uses scene_emotional_arc to pace the narration correctly
#   - Returns to narration_anchor image at least twice
#   - Ends on a concrete visual image, never a lesson
#   - Should sound like Studio Ghibli opening narration
#
#   Why it never sees the user input: prevents the story from being
#   too literal. The Writer only knows the metaphorical world.
#
# AGENT 3 — CINEMATOGRAPHER (run_cinematographer function in pipeline.py)
#   Input:  Director's brief JSON (NEVER sees fable text or user input)
#   Output: JSON with 5 video prompts, each with "prompt" and "duration" fields
#
#   What it does:
#   - Translates each scene beat into a precise Kling AI video prompt
#   - Uses visual_direction fields for consistent color/lighting across all 5
#   - NEVER shows character's face (always from behind/wide/silhouette/hands)
#   - Keeps character clothing and environment consistent across all 5 scenes
#   - Adds "studio ghibli inspired, soft watercolor animation" to every prompt
#
# ══════════════════════════════════════════════════════════════════════════════
# FILE STRUCTURE — what each file does
# ══════════════════════════════════════════════════════════════════════════════
#
# pipeline.py — MAIN FILE
#   - FastAPI server with 4 endpoints
#   - Three agent functions: run_director(), run_writer(), run_cinematographer()
#   - One shared API call function: call_claude()
#   - Director runs first, then Writer + Cinematographer run IN PARALLEL
#   - Two main endpoints:
#     POST /generate-story — agents only, no video/audio, ~15s, free to test
#     POST /generate       — full pipeline with Kling video + ElevenLabs audio
#   - Test endpoints:
#     GET /health          — check server and API keys
#     GET /test-story      — run hardcoded test input through agents
#     GET /test-all        — run all 5 test inputs, check diversity
#
# media.py — VIDEO AND AUDIO
#   - generate_one_clip(prompt, duration, scene_num) — one Kling API call
#   - generate_audio(fable_text, voice_tone) — one ElevenLabs API call
#   - generate_media_parallel(scenes, fable, voice_tone) — runs ALL 6 simultaneously
#   - Returns {video_urls: [5 urls], audio_b64: string, audio_duration_ms: int}
#   - If any clip fails it returns None for that position — never crashes
#   - If audio fails it returns None — never crashes
#
# test.py — TEST SCRIPT
#   - Run from terminal: python test.py
#   - python test.py "custom input"    — test custom input
#   - python test.py --all             — test all 5 inputs, check diversity
#   - python test.py --quality "input" — run with quality checks
#   - Built-in quality checker flags: banned words, generic characters,
#     missing tension in insights, face shots in Kling prompts
#
# .env — API KEYS (you create this from .env.example)
#   ANTHROPIC_API_KEY  — required right now for Claude API
#   KLING_API_KEY      — required for video generation
#   KLING_API_SECRET   — required for video generation (Kling uses HMAC auth)
#   ELEVENLABS_API_KEY — required for voice narration
#   IBM_API_KEY        — required to switch to watsonx.ai
#   IBM_PROJECT_ID     — required to switch to watsonx.ai
#   IBM_DB2_DSN        — required for session storage
#
# ══════════════════════════════════════════════════════════════════════════════
# DATA FLOW — exactly what gets passed between agents
# ══════════════════════════════════════════════════════════════════════════════
#
# User input string
#   → run_director(user_input)
#   → returns brief dict with these fields:
#       specific_true_thing   — the contradiction found in user's words
#       why_this_character    — structural reason for character choice
#       character             — unusual occupation in specific world
#       character_detail      — one physical habit/object making them real
#       scene_1 through scene_5 — "Object: / Action: / Shot:" format
#       scene_emotional_arc   — one sentence emotional movement across 5 scenes
#       embedded_insight      — the insight sentence with tension word
#       narration_anchor      — recurring physical image for the narration
#       visual_direction      — dict with color_temperature, lighting_quality,
#                               movement_style, atmosphere
#       voice_tone            — how ElevenLabs should narrate
#       insight_tag           — one word for org dashboard
#       severity              — mild / moderate / high
#
# brief dict
#   → run_writer(brief) AND run_cinematographer(brief) [in parallel]
#
# run_writer returns: fable string (120 words)
# run_cinematographer returns: scenes dict
#   {
#     "scene_1": {"prompt": "...", "duration": 6},
#     "scene_2": {"prompt": "...", "duration": 6},
#     "scene_3": {"prompt": "...", "duration": 6},
#     "scene_4": {"prompt": "...", "duration": 6},
#     "scene_5": {"prompt": "...", "duration": 6}
#   }
#
# fable + scenes + voice_tone
#   → generate_media_parallel() [in media.py]
#   → returns:
#       video_urls      — list of 5 video URL strings (some may be None)
#       audio_b64       — base64 encoded MP3 string (may be None)
#       audio_duration_ms — duration in milliseconds
#
# ══════════════════════════════════════════════════════════════════════════════
# WHAT THE FRONTEND NEEDS FROM THE API
# ══════════════════════════════════════════════════════════════════════════════
#
# The frontend (Person 2 — React app) calls POST /generate-story for testing
# and POST /generate for the full film.
#
# From /generate-story response, the frontend uses:
#   fable               — text to reveal word by word over the video
#   scenes              — 5 scene prompts (for reference, not used directly)
#   visual_direction    — color_temperature and atmosphere for canvas fallback
#   voice_tone          — pass to ElevenLabs when generating audio
#   insight_tag         — small text shown at end of film
#   reflection_line     — "A thought you might sit with: [embedded_insight]"; show after the fable/film so the meaning is a little clearer
#   show_crisis_resources — if true, show crisis resources prominently
#   crisis_note         — short message to show with crisis resources when show_crisis_resources is true
#   resources           — { disclaimer, crisis_help[], general_support }; always show disclaimer; when show_crisis_resources is true, highlight crisis_help (988, Crisis Text Line, etc.)
#   audio_duration_ms   — used to calculate word reveal timing
#                         word_delay_ms = audio_duration_ms / word_count
#
# From /generate response, additionally:
#   video_urls          — array of 5 URLs, play in sequence
#   audio_b64           — decode from base64, play as audio element
#
# WORD REVEAL TIMING:
#   const words = fable.split(' ')
#   const delay = audio_duration_ms / words.length
#   // reveal one word every `delay` milliseconds
#   // this makes text finish exactly when audio finishes
#
# VIDEO SEQUENCE:
#   // Play video_urls[0] first
#   // When it ends, play video_urls[1]
#   // Continue through all 5
#   // If a url is null, skip to next available
#   // After all 5, loop the last successful clip
#
# ══════════════════════════════════════════════════════════════════════════════
# SWITCHING FROM CLAUDE TO IBM WATSONX.AI
# ══════════════════════════════════════════════════════════════════════════════
#
# Currently: all 3 agents call Claude via call_claude() in pipeline.py
# To switch to IBM: replace call_claude() with this:
#
#   from ibm_watsonx_ai import APIClient, Credentials
#   from ibm_watsonx_ai.foundation_models import ModelInference
#
#   def call_claude(system_prompt: str, user_content: str, max_tokens: int = 1500) -> str:
#       credentials = Credentials(
#           url="https://us-south.ml.cloud.ibm.com",
#           api_key=os.getenv("IBM_API_KEY")
#       )
#       model = ModelInference(
#           model_id="meta-llama/llama-3-70b-instruct",
#           credentials=credentials,
#           project_id=os.getenv("IBM_PROJECT_ID"),
#           params={
#               "max_new_tokens": max_tokens,
#               "temperature": 0.8,
#               "repetition_penalty": 1.1,
#               "stop_sequences": ["Human:", "User:"]
#           }
#       )
#       full_prompt = f"System: {system_prompt}\n\nUser: {user_content}\n\nAssistant:"
#       return model.generate_text(full_prompt).strip()
#
# Also add to requirements.txt: ibm-watsonx-ai==1.1.2
# Also add to .env: IBM_API_KEY and IBM_PROJECT_ID
#
# The 3 system prompts (DIRECTOR_PROMPT, WRITER_PROMPT, CINEMATOGRAPHER_PROMPT)
# stay IDENTICAL — only the call_claude() function changes.
#
# ══════════════════════════════════════════════════════════════════════════════
# ADDING IBM DB2 SESSION STORAGE
# ══════════════════════════════════════════════════════════════════════════════
#
# Add this function to pipeline.py (after imports):
#
#   def save_to_db2(session_id, user_input, fable, insight_tag, severity):
#       try:
#           import ibm_db
#           conn = ibm_db.connect(os.getenv("IBM_DB2_DSN"), "", "")
#           sql = """INSERT INTO sessions
#                    (id, user_input, fable, insight_tag, severity, created_at)
#                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)"""
#           stmt = ibm_db.prepare(conn, sql)
#           ibm_db.bind_param(stmt, 1, session_id)
#           ibm_db.bind_param(stmt, 2, user_input[:500])
#           ibm_db.bind_param(stmt, 3, fable[:2000])
#           ibm_db.bind_param(stmt, 4, insight_tag)
#           ibm_db.bind_param(stmt, 5, severity)
#           ibm_db.execute(stmt)
#           sql2 = """INSERT INTO org_insights
#                     (id, insight_tag, severity, created_at)
#                     VALUES (?, ?, ?, CURRENT_TIMESTAMP)"""
#           stmt2 = ibm_db.prepare(conn, sql2)
#           ibm_db.bind_param(stmt2, 1, str(uuid.uuid4()))
#           ibm_db.bind_param(stmt2, 2, insight_tag)
#           ibm_db.bind_param(stmt2, 3, severity)
#           ibm_db.execute(stmt2)
#           ibm_db.close(conn)
#           print(f"✅ Saved to Db2: {session_id[:8]}")
#       except Exception as e:
#           print(f"⚠️ Db2 save failed (non-critical): {e}")
#
# Then call save_to_db2() at the end of generate_story() before return.
# Add ibm_db==3.2.3 to requirements.txt
#
# ══════════════════════════════════════════════════════════════════════════════
# QUALITY STANDARDS — what good output looks like
# ══════════════════════════════════════════════════════════════════════════════
#
# GOOD Director output:
#   specific_true_thing: "they say they have given up but keep describing
#                         new attempts — the contradiction is between stated
#                         resignation and continued trying"
#   character: "a tide-chart maker in a coastal town where the tides no
#               longer follow any predictable pattern"
#   embedded_insight: "the record of trying exists even though the tides
#                      ignore it, and that is both the grief and the thing
#                      that cannot be taken away"
#
# BAD Director output (too generic):
#   specific_true_thing: "they feel like their effort is not recognized"
#   character: "a young professional struggling in their career"
#   embedded_insight: "effort is never wasted"
#
# GOOD Writer output:
#   - Reads like Ghibli narration
#   - Has a recurring physical image
#   - Ends on something you can see
#   - Never uses banned words
#   - ~120 words
#
# BAD Writer output:
#   - Sounds like a wellness app
#   - States the lesson directly
#   - Uses words like "journey" or "healing"
#   - Ends with "remember that you are enough"
#
# GOOD Cinematographer output:
#   - Each prompt describes exactly one filmable shot
#   - Never mentions the character's face
#   - Includes lighting and film style in every prompt
#   - All 5 prompts feel like they belong to the same film
#
# BAD Cinematographer output:
#   - "A person feels sad" (not filmable)
#   - "Close-up of her face showing emotion" (shows face)
#   - Prompts with different styles across scenes
#
# ══════════════════════════════════════════════════════════════════════════════
# COMMON ERRORS AND FIXES
# ══════════════════════════════════════════════════════════════════════════════
#
# json.JSONDecodeError from Director or Cinematographer:
#   The LLM added markdown backticks around the JSON.
#   The parse_json() function handles this automatically.
#   If it still fails, the LLM may have added text before/after the JSON.
#   Fix: make the output instruction stricter —
#   add "Return ONLY the JSON. No text before it. No text after it."
#
# anthropic.AuthenticationError:
#   ANTHROPIC_API_KEY in .env is wrong or missing.
#   Check console.anthropic.com for the correct key.
#
# Writer returns more or fewer than 120 words:
#   Normal — LLM is approximate. Acceptable range is 110-130 words.
#   If consistently wrong, add "Count your words before returning." to Writer prompt.
#
# Cinematographer shows face in prompts:
#   Add this to CINEMATOGRAPHER_PROMPT: "Before returning, check every prompt.
#   If any prompt could show the character's face, rewrite it."
#
# Kling returns 401:
#   KLING_API_KEY or KLING_API_SECRET is wrong.
#   The HMAC signature in get_kling_headers() uses both.
#   Check klingai.com developer dashboard for correct values.
#
# All 5 Kling clips return None:
#   Either API key is wrong or free credits are exhausted.
#   Check klingai.com for credit balance.
#   The app still works without video — canvas animation is the fallback.
#
# ══════════════════════════════════════════════════════════════════════════════
# DO NOT CHANGE THESE THINGS
# ══════════════════════════════════════════════════════════════════════════════
#
# 1. The function signature of call_claude() — all 3 agents depend on it
# 2. The JSON field names in DIRECTOR_PROMPT output — Writer and Cinematographer
#    reference these fields by name
# 3. The parse_json() function — it handles edge cases from LLM output
# 4. The parallel execution in generate_story() — Writer + Cinematographer
#    must run in parallel after Director finishes
# 5. The None-safe handling in media.py — video_urls can contain None values
#    and the app must not crash when they do
#
# ══════════════════════════════════════════════════════════════════════════════
# TEAM RESPONSIBILITIES
# ══════════════════════════════════════════════════════════════════════════════
#
# Person 1 (you): pipeline.py and test.py — agents, prompts, tuning
# Person 2: React frontend — calls /generate-story then /generate
# Person 3: Kling + ElevenLabs — media.py is already written, needs API keys
# Person 4: IBM watsonx.ai + Db2 + Langflow — swap call_claude(), add save_to_db2()
#
# ══════════════════════════════════════════════════════════════════════════════
