from __future__ import annotations

import os
import json
import uuid
import concurrent.futures
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="NarrativeCare AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uses your OpenAI API key from .env (no base_url = official OpenAI API).
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── MENTAL HEALTH RESOURCES (always available; show prominently when show_crisis_resources is true) ──
MENTAL_HEALTH_RESOURCES = {
    "disclaimer": "NarrativeCare is a wellness reflection tool, not a substitute for professional care. If you're in crisis or need someone to talk to, please reach out.",
    "crisis_help": [
        {"name": "988 Suicide & Crisis Lifeline", "description": "Call or text 988 (US)", "url": "https://988lifeline.org"},
        {"name": "Crisis Text Line", "description": "Text HOME to 741741 (US)", "url": "https://www.crisistextline.org"},
        {"name": "International Association for Suicide Prevention", "description": "Global directory of crisis centers", "url": "https://www.iasp.info/resources/Crisis_Centres/"},
    ],
    "general_support": "If you're struggling, consider reaching out to a trusted person, campus counseling, or a mental health professional.",
}

# ── DIRECTOR PROMPT ───────────────────────────────────────────────────────────

DIRECTOR_PROMPT = """You are a creative director for a therapeutic storytelling system used in organizations — universities, hospitals, and companies.

A person has described a stressful or emotionally difficult situation. Your job is to reason deeply and produce a rich fable brief that becomes the creative foundation for a short personal film made specifically for this person.

═══════════════════════════════════════
STEP 0 — SAFETY (do this first, before any creative work)
═══════════════════════════════════════
Read the person's words once. If they suggest they or someone else may be at serious or immediate risk — for example: self-harm, suicide, abuse, feeling unsafe, or not wanting to go on — you MUST set "show_crisis_resources": true, "severity": "crisis", and "crisis_note" to one short, kind sentence we can show next to crisis resources (e.g. "If you need someone to talk to right now, please reach out."). Otherwise set "show_crisis_resources": false and "severity" to mild, moderate, or high as you would normally. This step ensures we take serious mental health seriously and direct people to proper help when needed.

═══════════════════════════════════════
ABSOLUTE RULES — never break these
═══════════════════════════════════════
- Never name emotions clinically: no anxiety, depression, stress, overwhelmed, burnout, trauma
- Never give advice, suggest solutions, or imply what the person should do
- Never use these words anywhere in your output: journey, path, weight, burden, healing, strength, storm, light at the end, grow, overcome, resilience
- The character must NOT be the user — they are a different person in a different world
- The insight must live inside what HAPPENS to the character — never stated as a lesson
- Every scene must be one single filmable camera shot — if you cannot picture the exact frame, rewrite it
- The insight must feel like recognition, not revelation — and must contain tension, not comfort
- Character and world must be structurally specific — not emotionally adjacent
- The character's occupation must be so unusual and specific that it could not appear on a list of 20 common occupations. If you would describe the character as a student, worker, professional, or any generic role — start over.
- The specific_true_thing must name a contradiction between what the person says and what their words reveal. If it does not contain the structure "they say X but their words show Y" it is not specific enough — start over.

═══════════════════════════════════════
REASONING STEPS — work through all 6
Write your reasoning for each step before moving on
═══════════════════════════════════════

STEP 1 — LISTEN DEEPLY
Read the input slowly, three times.
Find one specific word or phrase this person uses that most people would not notice — not the obvious emotion word, something underneath it.
Ask: what are they circling without landing on? What do they almost say but don't?
Write: "The word or phrase I noticed is [word] because [specific reason it reveals something]"

STEP 2 — THE SPECIFIC TRUE THING (find the contradiction)

Do NOT describe what they feel. Find the contradiction.

The contradiction is the gap between:
- What they CLAIM is true about their situation
- What their actual word choice REVEALS is true

Look for these specific patterns:
1. They say they want to stop doing something but describe continuing to do it in detail
2. They say they do not care but use language that shows they care deeply
3. They say they are confused but their words point clearly in one direction they are avoiding naming
4. They describe others as the problem but take total personal responsibility in how they frame it
5. They minimize their situation with words like 'just' or 'a bit' or 'kind of' while describing something serious

Example: if someone says 'I don't know if I still want to keep working as a doctor' — the word STILL is key. STILL implies they wanted it before and have not yet decided to stop. They are not someone who has walked away — they are someone asking for permission to feel what they already feel. Apply this kind of word-level reading to every input.

Name the contradiction in this exact format:
'They say [X] but the word [specific word] shows [Y]. The specific true thing is [one precise sentence that names the gap].'

Test: if you removed the person's name and showed this to 10 people who had never read the input, would it clearly describe this specific person and no one else? If not, make it more precise.

STEP 3 — THE CHARACTER AND WORLD (structural mirror)
First map the 5 structural elements of the person's situation:
- Effort vs result: working hard with poor results / working and unsure if it matters / effort invisible to others?
- Visibility: is their work or presence seen by others, or invisible?
- Agency: do they feel in control or acted upon by external forces?
- Other people: present and ignoring / absent / demanding / oblivious?
- Time orientation: waiting / rushing / stuck / moving but getting nowhere?

Then invent a character whose situation has THE SAME STRUCTURE across all 5 elements.
The character must have an unusual specific occupation or role — not "a student" or "a worker."
Think: lighthouse keeper on a coast where ships no longer pass, cartographer in a city whose streets change overnight, restorer who repairs undersides of famous paintings no one ever sees, tide-chart maker where tides follow no pattern.
The world must make the structural situation physically visible — the world externalizes the internal condition.

CRITICAL RULE: The character's world must be completely different from the person's real world. If the person works in a hospital, the character cannot be in a hospital or medical setting. If the person is a student, the character cannot be in a school or academic setting. If the person works in an office, the character cannot be in an office.
The character's occupation must require skill and dedication but exist in a world visually and contextually unrelated to the person's real situation. The mirror is structural — same effort/visibility/agency dynamics — but in a completely different world.
Ask yourself: if the person read this character description, would they immediately recognize their own job or setting? If yes, choose a completely different world.

Test: does every structural element map? Read them side by side. If effort-visibility doesn't match, rewrite the character.
Test: could this character apply to any other input today? If yes, make it more specific.
Write: "Structural map: [5 elements]. Character: [occupation] in a world where [specific condition]"

Find one specific physical detail about this character — a habit, a tool they carry, something about how they work — that makes them feel real and specific. This detail will appear in the narration.

STEP 4 — THE 5 SCENE BEATS (physical and filmable)
Each scene must be built around one specific physical object or detail that carries the emotional weight of that moment.
This is how film works — not through internal states but through physical things that stand in for them.

For each scene answer: Object / Action / Shot

Scene 1 — ESTABLISH
The character in their world. The problem is present but not yet named.
What specific object defines their situation? What is the character doing with or near it?
The camera sees: [filmable shot description]

Scene 2 — THE PROBLEM MADE PHYSICAL
The problem becomes something the camera can see.
Not "she feels unseen" — "she finishes her work and places it on the shelf, indistinguishable from 40 identical pieces no one has touched."
What physical thing makes the problem undeniable?

Scene 3 — THE LOWEST MOMENT
The character is alone with the object or situation. No movement. No action.
This should be the most still shot in the film.
What does complete stillness look like for this character?

Scene 4 — THE SMALL SHIFT
Not a solution. Not an epiphany.
One tiny physical thing changes or is noticed for the first time — something that was always there but unseen.
What detail shifts that the character (and viewer) suddenly sees?

Scene 5 — THE NEW IMAGE
The same world as scene 1. Same objects. But the character's relationship to them has changed — visible in how they stand, where they look, what they do with their hands.
What is physically different that shows internal change without stating it?

Describe the overall emotional arc across all 5 scenes in one sentence.

STEP 5 — THE INSIGHT (must pass 3 tests)
Connect directly to the contradiction from Step 2.
Must pass ALL THREE tests:
- Recognition test: would the person feel "I always knew that but could never say it" — not "I learned something new"?
- Resistance test: does it feel slightly uncomfortable or counterintuitive? If immediately comforting, it is a platitude.
- Specificity test: remove the character and world — does the insight still feel specific to this person, or is it generic?

Must contain a tension word: and / but / even though / while / despite. Your embedded_insight MUST include at least one of these words. Before returning the JSON, check: if embedded_insight does not contain one of them, rewrite the insight sentence to include one.
Write: "The insight is [sentence with tension word]. Tests: [apply all 3 — does it pass?]"
If it fails any test, rewrite until it passes all three.

FINAL CHECK before writing the insight:
Read the insight you just wrote. Now ask: does the fable need to STATE this anywhere, or will the viewer arrive at it themselves from watching what happens to the character?
If the insight can be stated as a sentence that begins with 'even though' or 'despite' or 'but' — it should NEVER appear in the fable text itself. It should only exist in this JSON field as a guide for what the story enacts.
The Writer agent will use this field to understand what the story is about — but the Writer is explicitly forbidden from stating it. The insight is the direction, not the destination.
Also: there must be NO reflection or explanation shown to the user after the fable. The film ends on the final image. Nothing is explained. If the frontend is showing a reflection or explanation, remove it.

STEP 6 — VISUAL DIRECTION AND VOICE
Based on your reading of this person's emotional state, make these visual decisions:
- Color temperature: warm amber / cool blue / neutral gray / shifting cool to warm / shifting warm to cool
- Lighting quality: soft diffused / harsh direct / low golden hour / flat overcast / single warm source in darkness
- Movement style: very slow and still / slow deliberate / gentle drift / slightly restless and searching
- Atmosphere: one sentence — the overall feeling of the world these 5 scenes inhabit
- Voice tone: how should ElevenLabs narrate this? Quality, pace, emotional register.

═══════════════════════════════════════
OUTPUT — return ONLY this JSON after completing all 6 steps
No markdown, no backticks, no other text
═══════════════════════════════════════
{
  "specific_true_thing": "the contradiction named precisely — one sentence",
  "why_this_character": "one sentence explaining the structural mirror — why this character was chosen based on the contradiction. This is what makes the story feel true not just poetic.",
  "character": "unusual occupation in specific world — one sentence",
  "character_detail": "one specific physical habit or object about this character that makes them real — not personality, something physical",
  "scene_1": "Object: ___ / Action: ___ / Shot: ___",
  "scene_2": "Object: ___ / Action: ___ / Shot: ___",
  "scene_3": "Object: ___ / Action: ___ / Shot: ___",
  "scene_4": "Object: ___ / Action: ___ / Shot: ___",
  "scene_5": "Object: ___ / Action: ___ / Shot: ___",
  "scene_emotional_arc": "one sentence describing emotional movement across all 5 scenes",
  "embedded_insight": "the insight sentence containing a tension word — and / but / even though / while / despite",
  "narration_anchor": "one specific concrete image or detail from the character's world that the narration should return to — the recurring physical thing that carries the story's meaning",
  "visual_direction": {
    "color_temperature": "warm amber | cool blue | neutral gray | shifting cool to warm | shifting warm to cool",
    "lighting_quality": "soft diffused | harsh direct | low golden hour | flat overcast | single warm source in darkness",
    "movement_style": "very slow and still | slow deliberate | gentle drift | slightly restless",
    "atmosphere": "one sentence — the overall feeling of the world"
  },
  "voice_tone": "narration quality — pace, warmth, emotional register",
  "insight_tag": "one word for anonymous org dashboard",
  "severity": "mild | moderate | high | crisis",
  "show_crisis_resources": false,
  "crisis_note": "optional — one short sentence to show with crisis resources only when show_crisis_resources is true"
}"""


# ── WRITER PROMPT ─────────────────────────────────────────────────────────────

WRITER_PROMPT = """You are a fable writer for a therapeutic film system.

You receive a rich director brief. Write a 120-word fable narration that will be read aloud over a 30-second film made for one specific person.

═══════════════════════════════════════
USE THESE FIELDS FROM THE BRIEF
═══════════════════════════════════════
- why_this_character: this is the structural reason this character mirrors the person. Use this to make the narration feel precisely true — not just poetic.
- character_detail: weave this physical detail into the narration at least once. It is what makes the character feel real.
- scene_emotional_arc: let this guide your pacing. The heaviest scene should feel heaviest in the narration — slower words, shorter sentences. The shift scene should feel lighter.
- narration_anchor: return to this specific image or detail at least twice. Once near the beginning, once near or at the end. This creates resonance.
- embedded_insight: the story must enact this. Never state it. The viewer should feel it without being told.
- voice_tone: write so that reading aloud in this tone feels natural.

═══════════════════════════════════════
ABSOLUTE RULES
═══════════════════════════════════════
- Third person only — "There was a..." not "You are..."
- Character mirrors the person's situation but is not them
- The insight is enacted by what happens — NEVER stated
- Never use: journey, path, weight, burden, healing, strength, you should, remember that, it is okay, purpose, determined, resolve, realize, understand
- Written to be read aloud — rhythm and pacing matter as much as meaning
- Exactly 120 words — count carefully before returning
- Should sound like the opening narration of a Studio Ghibli film — warm, specific, unhurried, slightly melancholy

ENDING RULE — this is the most important rule:
The final sentence must describe something the camera can see.
Not what the character feels. Not what they decide. Not what they realize. What the camera sees.

Good ending examples:
'The chisel resumed its rhythm against the stone.'
'She placed the chart in her bag and walked toward the door.'
'The dust settled slowly in the empty workshop.'

Bad ending examples (DO NOT end like this):
'...with a determined expression' — describes emotion
'...ready to face the world' — explains meaning
'...not just for recognition but for the craft itself' — states lesson
'...feeling hope for the first time' — describes feeling

Before returning the fable, read your final sentence.
Ask: is this something a camera can literally film?
If you describe how the character FEELS or what they REALIZE or what they are NOW READY FOR — delete those words and replace with what the camera sees instead.

═══════════════════════════════════════
OUTPUT
═══════════════════════════════════════
Return ONLY the fable narration text.
No title. No word count label. No quotation marks. Just the story."""


# ── CINEMATOGRAPHER PROMPT ────────────────────────────────────────────────────

CINEMATOGRAPHER_PROMPT = """You are a cinematographer for a therapeutic short film system.

You receive a rich director brief with visual direction already decided. Your job is to translate each of the 5 scene beats into a precise video generation prompt for Kling AI.

═══════════════════════════════════════
USE THESE FIELDS FROM THE BRIEF
═══════════════════════════════════════
- visual_direction.color_temperature: apply this to every single prompt — describe the lighting and color in these terms
- visual_direction.lighting_quality: use this exact lighting quality in every scene
- visual_direction.movement_style: camera movement must match this across all 5 clips — if "very slow and still" then no fast movement in any clip
- visual_direction.atmosphere: this is the world all 5 clips inhabit — every prompt should feel like it belongs to this same world
- character: keep the occupation and world consistent across all 5 scenes
- character_detail: include this physical detail in at least one scene prompt

These parameters came from the Director's reading of this specific person's emotional state. They are not suggestions — they are the visual language of this specific film.

═══════════════════════════════════════
ABSOLUTE RULES FOR EVERY PROMPT
═══════════════════════════════════════
- NEVER show the character's face directly — always one of: shot from behind / wide shot where figure is small / silhouette / close on hands or feet only. Do not use the word "face" in any prompt unless you explicitly say "face not visible" or "from behind".
- Visual style in EVERY prompt: "studio ghibli inspired, soft watercolor animation, warm painterly illustration style, hand-drawn"
- Keep character clothing and environment consistent across all 5 scenes
- Each prompt is 2-3 sentences minimum and at least 40 characters — precise and visual, not abstract
- Duration is always 6 seconds
- The 5 scenes must feel like they belong to the same film — same world, same light, same character

═══════════════════════════════════════
PROMPT STRUCTURE FOR EACH SCENE
Sentence 1: What the character is doing and where (include character_detail if relevant)
Sentence 2: Shot type, camera position, what is in frame
Sentence 3: Lighting, color, atmosphere, visual style tag
═══════════════════════════════════════

SELF-CHECK before returning JSON:
Read every single prompt you wrote. For each one ask:
1. Could this prompt result in a shot that shows the character's face? If yes — rewrite it. Use: 'shot from behind' or 'figure visible only as silhouette' or 'close on hands' or 'wide shot, character small in frame'
2. Does this prompt contain abstract emotional language like 'feeling determined' or 'sense of purpose' or 'emotional moment'? If yes — remove it. Replace with what the camera physically sees.

A Kling AI prompt must describe ONLY what is physically in the frame. No emotions. No internal states. Only objects, movements, lighting, and composition.

═══════════════════════════════════════
OUTPUT — return ONLY this JSON
No markdown, no backticks, no other text
═══════════════════════════════════════
{
  "scene_1": {"prompt": "...", "duration": 6},
  "scene_2": {"prompt": "...", "duration": 6},
  "scene_3": {"prompt": "...", "duration": 6},
  "scene_4": {"prompt": "...", "duration": 6},
  "scene_5": {"prompt": "...", "duration": 6}
}"""


# ── AGENT FUNCTIONS ───────────────────────────────────────────────────────────

def call_claude(system_prompt: str, user_content: str, max_tokens: int = 1500) -> str:
    """Single reusable LLM API call (OpenAI API)."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=max_tokens,  # vLLM/HF endpoint expects max_tokens
    )
    raw = response.choices[0].message.content
    if raw is None:
        raise ValueError(
            "GPT-OSS server returned empty content. "
            "Server may be overloaded (avoid hogging the API) or the model name/endpoint may have changed — ask in 🎓┃help-center."
        )
    # Some servers return content as a list of parts; normalize to string
    if isinstance(raw, list):
        text = "".join(
            p.get("text", p) if isinstance(p, dict) else str(p)
            for p in raw
        ).strip()
    else:
        text = (raw or "").strip()
    if not text:
        raise ValueError("GPT-OSS server returned empty text. Try again or check 🎓┃help-center.")
    return text


def parse_json(text: str, agent_name: str) -> dict:
    """Parse JSON from agent output, handling markdown code blocks and common LLM issues."""
    clean = text.strip()
    clean = clean.replace("```json", "").replace("```", "").strip()
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"{agent_name} returned no JSON. Raw output: {clean[:300]}")
    json_str = clean[start:end]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        json_str = json_str.replace("\n", " ").replace("\r", "")
        return json.loads(json_str)


def run_director(user_input: str) -> dict:
    """
    Agent 1: Reads raw user input.
    Reasons through 6 steps to produce rich fable brief.
    Returns brief as dict.
    """
    print(f"\n{'─'*50}")
    print(f"🎬 DIRECTOR running...")
    print(f"   Input: {user_input[:80]}...")

    text  = call_claude(DIRECTOR_PROMPT, f"Situation: {user_input}", max_tokens=4096)
    brief = parse_json(text, "Director")

    print(f"✅ Director complete")
    print(f"   Character:  {brief.get('character', '')[:70]}")
    print(f"   True thing: {brief.get('specific_true_thing', '')[:70]}")
    print(f"   Insight:    {brief.get('embedded_insight', '')[:70]}")
    return brief


def run_writer(brief: dict) -> str:
    """
    Agent 2: Reads Director brief only — never sees raw user input.
    Writes 120-word fable narration.
    Returns fable as string.
    """
    print(f"\n✍️  WRITER running...")

    fable = call_claude(
        WRITER_PROMPT,
        f"Director brief:\n{json.dumps(brief, indent=2)}",
        max_tokens=600
    )
    word_count = len(fable.split())
    print(f"✅ Writer complete — {word_count} words")
    print(f"   Preview: {fable[:100]}...")
    return fable


def run_cinematographer(brief: dict) -> dict:
    """
    Agent 3: Reads Director brief only — never sees fable text.
    Produces 5 video prompts with consistent visual direction.
    Returns scenes dict.
    """
    print(f"\n🎥 CINEMATOGRAPHER running...")

    text   = call_claude(
        CINEMATOGRAPHER_PROMPT,
        f"Director brief:\n{json.dumps(brief, indent=2)}",
        max_tokens=1000
    )
    scenes = parse_json(text, "Cinematographer")

    print(f"✅ Cinematographer complete — {len(scenes)} scenes")
    for i in range(1, 6):
        key = f"scene_{i}"
        if key in scenes:
            print(f"   Scene {i}: {scenes[key]['prompt'][:80]}...")
    return scenes


def _quality_check_and_agents(brief: dict, fable: str, scenes: dict) -> tuple[list[str], set[str]]:
    """
    Same checks as test.py quality_check. Returns (list of issue messages, set of agent names to retry).
    Only retry the agent that produced the failing output: director | writer | cinematographer.
    """
    issues = []
    agents_to_retry = set()

    character = brief.get("character", "")
    insight = brief.get("embedded_insight", "")

    # Director: insight tension, generic character
    tension_words = ["and", "but", "even though", "while", "despite"]
    if not any(w in (insight or "").lower() for w in tension_words):
        issues.append(f"Insight has no tension word: '{insight}'")
        agents_to_retry.add("director")
    generic = ["young professional", "student", "worker", "employee", "person"]
    for g in generic:
        if g in (character or "").lower():
            issues.append(f"Character may be generic: '{character}'")
            agents_to_retry.add("director")
            break

    # Writer: word count, banned words, lesson ending
    word_count = len((fable or "").split())
    if word_count < 100 or word_count > 140:
        issues.append(f"Fable word count is {word_count} — should be ~120")
        agents_to_retry.add("writer")
    banned = ["journey", "path", "weight", "burden", "healing", "strength",
              "purpose", "determined", "resolve", "realize", "understand"]
    fable_lower = (fable or "").lower()
    for word in banned:
        if word in fable_lower:
            issues.append(f"Fable contains banned word: '{word}'")
            agents_to_retry.add("writer")
            break
    last_sentence = (fable or "").split(".")[-2] if "." in (fable or "") else (fable or "")[-100:]
    for w in ["remember", "you should", "it is okay", "never forget", "learn"]:
        if w in last_sentence.lower():
            issues.append(f"Fable may end with a lesson: '...{last_sentence}'")
            agents_to_retry.add("writer")
            break

    # Cinematographer: face in scene, short prompt
    for i in range(1, 6):
        prompt = (scenes or {}).get(f"scene_{i}", {}).get("prompt", "")
        if "face" in prompt.lower() and "no face" not in prompt.lower():
            issues.append(f"Scene {i} may show character's face")
            agents_to_retry.add("cinematographer")
        if len(prompt) < 40:
            issues.append(f"Scene {i} prompt too short: '{prompt}'")
            agents_to_retry.add("cinematographer")

    return issues, agents_to_retry


# ── REQUEST MODELS ────────────────────────────────────────────────────────────

class StoryRequest(BaseModel):
    user_input: str

class FullRequest(BaseModel):
    user_input: str


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

MAX_QUALITY_RETRIES = 2  # Targeted retries: only re-run the agent(s) that failed quality


def _build_story_response(session_id: str, brief: dict, fable: str, scenes: dict) -> dict:
    """Build the JSON response for generate_story from brief, fable, scenes. No reflection/explanation after the fable — film ends on the final image only."""
    show_crisis = brief.get("show_crisis_resources") is True
    return {
        "session_id":            session_id,
        "fable":                 fable,
        "scenes":                scenes,
        "specific_true_thing":   brief.get("specific_true_thing", ""),
        "why_this_character":   brief.get("why_this_character", ""),
        "character":            brief.get("character", ""),
        "character_detail":      brief.get("character_detail", ""),
        "scene_emotional_arc":  brief.get("scene_emotional_arc", ""),
        "embedded_insight":     brief.get("embedded_insight", ""),
        "narration_anchor":     brief.get("narration_anchor", ""),
        "visual_direction":      brief.get("visual_direction", {}),
        "voice_tone":           brief.get("voice_tone", "warm, quiet, unhurried"),
        "insight_tag":          brief.get("insight_tag", "reflection"),
        "severity":             brief.get("severity", "moderate"),
        "show_crisis_resources": show_crisis,
        "crisis_note":          brief.get("crisis_note", "") if show_crisis else "",
        "resources":            MENTAL_HEALTH_RESOURCES,
    }


@app.post("/generate-story")
async def generate_story(req: StoryRequest):
    """
    Story agents only — Director → Writer + Cinematographer (parallel).
    On quality failure, only the agent(s) that failed are re-run (no full rebuild).
    """
    if not req.user_input or len(req.user_input.strip()) < 10:
        raise HTTPException(400, "Please describe your situation in more detail.")

    session_id = str(uuid.uuid4())
    print(f"\n{'='*50}")
    print(f"SESSION: {session_id[:8]}")
    print(f"{'='*50}")

    try:
        brief = run_director(req.user_input)
        print(f"\n⚡ Running Writer + Cinematographer in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            writer_future = executor.submit(run_writer, brief)
            cinema_future = executor.submit(run_cinematographer, brief)
            fable = writer_future.result()
            scenes = cinema_future.result()

        for attempt in range(MAX_QUALITY_RETRIES + 1):
            issues, to_retry = _quality_check_and_agents(brief, fable, scenes)
            if not issues:
                print(f"\n{'='*50}")
                print(f"✅ PIPELINE COMPLETE — session {session_id[:8]}")
                print(f"{'='*50}\n")
                return _build_story_response(session_id, brief, fable, scenes)

            if attempt == MAX_QUALITY_RETRIES:
                print(f"\n⚠️  Quality issues remain after {MAX_QUALITY_RETRIES + 1} attempt(s): {issues}")
                print(f"{'='*50}\n")
                return _build_story_response(session_id, brief, fable, scenes)

            print(f"\n⚠️  Quality issues — retrying only: {sorted(to_retry)}")
            if "director" in to_retry:
                brief = run_director(req.user_input)
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    writer_future = executor.submit(run_writer, brief)
                    cinema_future = executor.submit(run_cinematographer, brief)
                    fable = writer_future.result()
                    scenes = cinema_future.result()
            else:
                if "writer" in to_retry:
                    fable = run_writer(brief)
                if "cinematographer" in to_retry:
                    scenes = run_cinematographer(brief)

        return _build_story_response(session_id, brief, fable, scenes)

    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Agent returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"LLM error: {str(e)}")


@app.post("/generate")
async def generate_full(req: FullRequest):
    """
    Full pipeline — story agents + Kling video + ElevenLabs audio.
    Takes ~75-90 seconds. Costs Kling + ElevenLabs credits.
    Use this when story quality is confirmed and you want the film.
    """
    if not req.user_input or len(req.user_input.strip()) < 10:
        raise HTTPException(400, "Please describe your situation in more detail.")

    # Import here to avoid errors if media keys not set up yet
    try:
        from media import generate_media_parallel
    except ImportError:
        raise HTTPException(500, "media.py not found — make sure it is in the same folder")

    session_id = str(uuid.uuid4())
    print(f"\n{'='*50}")
    print(f"FULL PIPELINE SESSION: {session_id[:8]}")
    print(f"{'='*50}")

    try:
        # Step 1: Director
        brief = run_director(req.user_input)

        # Step 2: Writer + Cinematographer in parallel
        print(f"\n⚡ Running Writer + Cinematographer in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            writer_future = executor.submit(run_writer, brief)
            cinema_future = executor.submit(run_cinematographer, brief)
            fable  = writer_future.result()
            scenes = cinema_future.result()

        # Step 3: Video + Audio in parallel
        print(f"\n⚡ Running Kling + ElevenLabs in parallel...")
        media = generate_media_parallel(
            scenes,
            fable,
            brief.get("voice_tone", "warm, quiet, unhurried")
        )

        print(f"\n{'='*50}")
        print(f"✅ FULL PIPELINE COMPLETE — session {session_id[:8]}")
        print(f"{'='*50}\n")

        show_crisis = brief.get("show_crisis_resources") is True
        return {
            "session_id":            session_id,
            "fable":                 fable,
            "scenes":                scenes,
            "video_urls":            media["video_urls"],
            "audio_b64":             media["audio_b64"],
            "audio_duration_ms":     media["audio_duration_ms"],
            "specific_true_thing":   brief.get("specific_true_thing", ""),
            "why_this_character":   brief.get("why_this_character", ""),
            "character":            brief.get("character", ""),
            "scene_emotional_arc":  brief.get("scene_emotional_arc", ""),
            "embedded_insight":     brief.get("embedded_insight", ""),
            "visual_direction":      brief.get("visual_direction", {}),
            "voice_tone":           brief.get("voice_tone", "warm, quiet, unhurried"),
            "insight_tag":          brief.get("insight_tag", "reflection"),
            "severity":             brief.get("severity", "moderate"),
            "show_crisis_resources": show_crisis,
            "crisis_note":          brief.get("crisis_note", "") if show_crisis else "",
            "resources":            MENTAL_HEALTH_RESOURCES,
        }

    except Exception as e:
        raise HTTPException(500, f"Pipeline error: {str(e)}")


# ── HEALTH AND TESTING ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Check server status and which API keys are loaded."""
    return {
        "status": "running",
        "keys": {
            "openai":     "✅ present" if os.getenv("OPENAI_API_KEY")       else "❌ MISSING — add OPENAI_API_KEY to .env",
            "kling":      "✅ present" if os.getenv("KLING_API_KEY")        else "⚠️  missing — needed for video",
            "elevenlabs": "✅ present" if os.getenv("ELEVENLABS_API_KEY")   else "⚠️  missing — needed for audio",
        },
        "endpoints": {
            "test_story":    "GET  /test-story   — run test with hardcoded input (free)",
            "story_only":    "POST /generate-story — agents only, no video (free, ~15s)",
            "full_pipeline": "POST /generate       — full film with video+audio (~90s)",
            "api_docs":      "GET  /docs           — interactive API documentation",
        }
    }


TEST_INPUTS = [
    "I've been studying for weeks and I just failed my midterm and I feel like all my effort means nothing",
    "My manager never acknowledges my work and I've been here 8 months and I feel completely invisible",
    "I feel like I'm slowly losing my friend group and I don't know how to stop it",
    "I have 4 deadlines this week and I keep starting things and not finishing any of them",
    "I moved to a new city 6 months ago and I still feel like a stranger everywhere I go",
    "I'm a doctor. It's been a long day, I've seen a bunch of patients and I'm very stressed. I'm in a hospital. I don't know what to do. I don't know if I still want to keep working as a doctor.",
]

@app.get("/test-story")
async def test_story():
    """
    Test with hardcoded input — runs all 3 agents, returns full story JSON.
    Free to call as many times as you want. Use this to evaluate prompt quality.
    Takes ~15 seconds.
    """
    req = StoryRequest(user_input=TEST_INPUTS[0])
    return await generate_story(req)


@app.get("/test-all")
async def test_all_inputs():
    """
    Run all 5 test inputs and return results side by side.
    Use this to check that each input produces a different character and world.
    Takes ~75 seconds (5 × 15s running sequentially).
    """
    results = []
    for i, input_text in enumerate(TEST_INPUTS):
        print(f"\n{'─'*40}")
        print(f"Test {i+1}/5: {input_text[:60]}...")
        req = StoryRequest(user_input=input_text)
        try:
            result = await generate_story(req)
            results.append({
                "input":              input_text,
                "character":          result["character"],
                "specific_true_thing": result["specific_true_thing"],
                "embedded_insight":   result["embedded_insight"],
                "fable_preview":      result["fable"][:150] + "...",
                "scene_1_preview":    result["scenes"].get("scene_1", {}).get("prompt", "")[:100],
            })
        except Exception as e:
            results.append({"input": input_text, "error": str(e)})

    return {
        "summary": "Check that all 5 characters are completely different. If any two feel similar, the Director prompt needs tightening.",
        "results": results
    }
