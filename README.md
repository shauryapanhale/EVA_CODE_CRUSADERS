# EVA – Enhanced Virtual Assistant (Windows) 🤖

A JARVIS‑style desktop assistant for Windows that listens for “JARVIS”, understands natural commands locally using Ollama (Mistral LLM), analyzes the screen with Omniparser + Gemini, and executes actions via keyboard/mouse/system executors.

---

## ✅ What you need (install these)

1) Windows 10/11 (64‑bit), microphone enabled
2) Python 3.8+ (check “Add Python to PATH” during install)
3) Git for Windows
4) C compiler (MinGW GCC) for building executors
5) Ollama (local LLM runtime)
6) Mistral model for Ollama (downloaded inside Ollama)
7) Google Gemini API key (free) for screen analysis
8) Stable internet only for the one‑time downloads above

---

## 📦 Quick setup (one‑time)

Open PowerShell and follow these steps.

1) Clone and enter the project
git clone https://github.com/shauryapanhale/EVA_CODE_CRUSADERS.git
cd EVA_CODE_CRUSADERS

2) Create and activate a virtual environment
python -m venv eva_env
eva_env\Scripts\activate

3) Install Python dependencies
pip install -r requirements.txt

4) Install Ollama (download and run the Windows installer)
- Go to https://ollama.ai and install
- Then pull the Mistral model:
ollama pull mistral
Verify:
ollama list
You should see: mistral:latest

5) Add your Gemini API key
- Get a free key at: https://makersuite.google.com/app/apikey
- Create a file named .env in the project root with:
GEMINI_API_KEY=your_key_here
Alternatively you can put the key into config.py if that’s how your code reads it.

6) Install MinGW (GCC) and add to PATH (only if you don’t have gcc)
- Download MinGW from SourceForge (mingw-get installer)
- During installation, select mingw32-gcc
- Add C:\MinGW\bin to your PATH
- Open a fresh PowerShell and confirm:
gcc --version

7) Build the C executors (if not already present)
cd execution\c_executors
gcc -shared -o executor.dll executor.c system_commands.c -luser32 -lgdi32
cd ....

8) (Optional) Pre‑download Whisper model to avoid first‑run delay
python -c "from faster_whisper import WhisperModel; WhisperModel('large-v2', device='cpu', compute_type='int8')"

---

## ▶️ How to run (every time)

You need two terminals.

Terminal A – start Ollama service:
ollama serve
Keep it running.

Terminal B – run EVA:

cd EVA_CODE_CRUSADERS
eva_env\Scripts\activate
python main.py

You should see it listening for the wake word.

---

## 🗣️ What to say

- Activate: “JARVIS”
- System: “set volume to 50”, “increase brightness”, “mute”
- Apps: “open spotify”, “open chrome”, “open calculator”, “close window”
- Media: “play music”, “pause”, “next song”, “previous track”
- Web: “search for python tutorials”, “go to youtube”
- End: “goodbye jarvis”

Tips:
- Speak clearly after the wake word
- Leave ~1 sec pause after “JARVIS” before your command
- Keep commands within 10 seconds (default recording window)

---

## 🧱 Project structure (important folders)

EVA_CODE_CRUSADERS/
├─ main.py # Entry point
├─ config.py # Configs (can point to .env)
├─ requirements.txt # Python deps
├─ .env # Put GEMINI_API_KEY here (do not commit)
├─ execution/
│ ├─ action_router.py # Routes actions to executors
│ ├─ system_executor.py # Volume/brightness/power
│ └─ c_executors/ # Low-level executors (C)
│ ├─ executor.c
│ ├─ system_commands.c
│ └─ executor.dll # Built artifact
├─ models/
│ ├─ semantic_classifier.py # Uses Ollama (Mistral) for intent
│ ├─ command_processor.py # Validates, extracts entities
│ └─ (fallback models) # If you keep classical classifiers
├─ speech/
│ ├─ speech_to_text.py # Faster Whisper
│ ├─ text_to_speech.py
│ └─ wake_word_detector.py # Porcupine
├─ vision/
│ ├─ screen_analyzer.py # Gemini + Omniparser glue
│ ├─ screenshot_handler.py
│ └─ omniparser_executor.py
├─ utils/ # Logger, helpers, etc.
└─ weights/ # Model weights (e.g., Omniparser)

---

## 🔧 Troubleshooting

- Ollama error 404
  - Cause: Model not pulled or service not running
  - Fix:
    ```
    ollama pull mistral
    ollama serve
    ```

- “gcc not found”
  - Install MinGW, add C:\MinGW\bin to PATH, reopen PowerShell, run `gcc --version`

- Wake word not detected
  - Check microphone input device in Windows Sound Settings
  - Reduce background noise, speak clearly “JARVIS”

- Very slow first run
  - First time downloads and model warm‑up; subsequent runs are faster
  - Pre‑download Whisper as shown above

- Volume doesn’t change
  - Ensure system_executor’s volume path uses pycaw or fallback is enabled
  - Optionally: `pip install pycaw`

- “Module not found”
  - Make sure the venv is active and `pip install -r requirements.txt` completed

---

## 🛡️ Notes on privacy

- Speech recognition, LLM, and execution run locally
- Internet is only required for one‑time downloads (models, dependencies) and Gemini vision calls
- Keep your API keys in `.env` and do not commit them

---

## 🧪 Quick smoke test

1) Start Ollama:
ollama serve
2) Run EVA:
eva_env\Scripts\activate
python main.py
3) Say: “JARVIS … open notepad”
4) Say: “set volume to 30”
5) Say: “goodbye jarvis”

You should see the app open, volume adjust, and session end cleanly.

---

## 📄 License

MIT – free to use and modify for learning and projects.
If you also want the exact git push steps for your repo, run these in PowerShell from your project folder:
git remote set-url origin https://github.com/shauryapanhale/EVA_CODE_CRUSADERS.git
git add .
git commit -m "📝 Add complete README and setup instructions"
git push -u origin main
If the branch is not main yet:
git branch -M main
git push -u origin main --force


