# Ceaser-AI / Aegis OS

A structured-first autonomous desktop agent with multi-modal capabilities.

## Features
- **Text Mode**: Input commands via text.
- **Speech Mode**: Give voice commands using your microphone.
- **Vision Mode**: Upload images for context or let the agent see the screen (Vision Fallback).
- **Structured Perception**: Uses Windows APIs to understand the OS state without screenshots (fast & cheap).
- **Groq Reasoning**: Uses Llama 3 / Mixtral on Groq for high-speed planning.
- **Vision Fallback**: Uses Gemini 2.0 Flash when structured data is insufficient.

## Installation

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration**:
    - Open `openclaw/config.yaml`.
    - Set your `GROQ_API_KEY` and `GEMINI_API_KEY`.
    - Alternatively, set them as environment variables.

## Usage

### Native GUI (Recommended)
Run the modern desktop interface:
```bash
python gui.py
```
This launches a standalone window with:
- Dark mode & futuristic UI.
- Voice input toggle.
- Screen vision toggle.
- Real-time chat & status updates.

### Web UI (Legacy)
Run the Streamlit interface:
```bash
streamlit run ui.py
```

### CLI Mode
Run the agent directly from the command line:
```bash
python main.py "Your goal here"
```
Example:
```bash
python main.py "Open Notepad and type Hello World"
```

## Architecture
- **Core**: `openclaw/` - Manages the agent lifecycle.
- **Skills**: `skills/` - Modular capabilities (Perception, Planning, Execution).
- **UI**: `ui.py` - User interface.

## Troubleshooting
- If `pyaudio` fails to install, you may need `portaudio` or use a pre-built wheel.
- Ensure you have valid API keys for full functionality.
