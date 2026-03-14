# NarrativeCare AI — Backend

3-agent AI pipeline generating a 30-second personal fable film.

## What's in this folder

| File | What it does |
|---|---|
| `pipeline.py` | Main server — 3 AI agents + API endpoints |
| `media.py` | Kling video + ElevenLabs audio generation |
| `test.py` | Test script — run from command line |
| `requirements.txt` | Python dependencies |
| `.env.example` | API key template — copy to `.env` |

---

## Setup — do this once

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your .env file

```bash
cp .env.example .env
```

Open `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Leave Kling and ElevenLabs blank for now — story agents work without them.

### 3. Start the server

```bash
uvicorn pipeline:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

---

## Test it works — do this right after starting

### Quick health check
Open browser: `http://localhost:8000/health`

Should show:
```json
{
  "status": "running",
  "keys": {
    "anthropic": "✅ present",
    "kling": "⚠️ missing — needed for video",
    "elevenlabs": "⚠️ missing — needed for audio"
  }
}
```

### Run first story test
Open browser: `http://localhost:8000/test-story`

OR in a new terminal:
```bash
python test.py
```

Takes ~15 seconds. You will see the full JSON output including the fable, 5 scene prompts, visual direction, and insight.

---

## Test your own inputs

### Using the test script (recommended)

```bash
# Test with your own situation
python test.py "I failed my midterm after studying for weeks"

# Test all 5 built-in inputs and check diversity
python test.py --all

# Test with quality checks
python test.py --quality "I feel invisible at work"
```

### Using curl

```bash
curl -X POST http://localhost:8000/generate-story \
  -H "Content-Type: application/json" \
  -d '{"user_input": "I failed my midterm after studying for weeks"}'
```

### Using the interactive docs
Open browser: `http://localhost:8000/docs`
Click `/generate-story` → Try it out → Enter your input → Execute

---

## What to check in each output

Read every output and ask these questions:

**Is the character specific?**
Good: "a cartographer in a city whose streets change overnight"
Bad: "a young professional struggling at work"

**Does the specific_true_thing name a contradiction?**
Good: "they say they have given up but their words show they are still trying"
Bad: "they feel like their effort means nothing"

**Does the insight contain tension?**
Good: "the work was real even though no one witnessed it, and that is the thing they cannot decide whether to grieve or keep"
Bad: "effort is never wasted"

**Are the 5 scene prompts filmable?**
Each should describe exactly what a camera would see.
Check: does it include a physical object, a shot type, lighting?

**Does the fable end on an image?**
Should end with something you can see, not a lesson.

**If any output feels generic** — run `python test.py --all` and paste the outputs here to get the Director prompt tightened.

---

## API Endpoints

| Endpoint | Method | Use |
|---|---|---|
| `/health` | GET | Check server + API keys |
| `/test-story` | GET | Test agents with hardcoded input |
| `/generate-story` | POST | Story agents only — fast, free, use for tuning |
| `/generate` | POST | Full pipeline with video + audio |
| `/test-all` | GET | Run all 5 test inputs, check diversity |
| `/docs` | GET | Interactive API documentation |

---

## For Person 2 (Frontend)

Call `/generate-story` while testing, switch to `/generate` when video keys are set up.

```javascript
const response = await fetch('http://localhost:8000/generate-story', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ user_input: userText })
});
const data = await response.json();

// data.fable           — text to reveal word by word
// data.scenes          — 5 scene objects with prompts
// data.visual_direction — color, lighting, movement for canvas fallback
// data.voice_tone      — pass to ElevenLabs settings
// data.insight_tag     — show at end of film
// data.audio_duration_ms — sync word reveal timing to this
```

For full pipeline (with video):
```javascript
// Same call but POST to /generate instead
// data.video_urls      — array of 5 video URLs to play in sequence
// data.audio_b64       — base64 audio to decode and play
```

---

## For Person 4 (IBM)

To switch from Claude to IBM watsonx.ai, find the `call_claude()` function in `pipeline.py` and replace it:

```python
# Replace this:
def call_claude(system_prompt, user_content, max_tokens=1500):
    response = client.messages.create(
        model="claude-opus-4-5",
        ...
    )

# With this:
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

def call_claude(system_prompt, user_content, max_tokens=1500):
    model = ModelInference(
        model_id="meta-llama/llama-3-70b-instruct",
        credentials=Credentials(url="https://us-south.ml.cloud.ibm.com", api_key=os.getenv("IBM_API_KEY")),
        project_id=os.getenv("IBM_PROJECT_ID"),
        params={"max_new_tokens": max_tokens, "temperature": 0.8}
    )
    full_prompt = f"System: {system_prompt}\n\nUser: {user_content}"
    return model.generate_text(full_prompt)
```

The 3 system prompts stay identical — just the API call changes.

---

## Common errors

**`ModuleNotFoundError: No module named 'anthropic'`**
Run: `pip install -r requirements.txt`

**`anthropic.AuthenticationError`**
Your ANTHROPIC_API_KEY in `.env` is wrong. Check console.anthropic.com for the correct key.

**`json.JSONDecodeError` in Director or Cinematographer**
The LLM returned text with markdown backticks. This is handled automatically by `parse_json()` but if it persists, add more examples to the prompt of the failing agent.

**`Connection refused` on port 8000**
Server is not running. Run: `uvicorn pipeline:app --reload --port 8000`

**Kling returns 401**
Your KLING_API_KEY or KLING_API_SECRET is wrong. Check klingai.com developer dashboard.
