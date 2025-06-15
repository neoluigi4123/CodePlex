# CodePlex V2⚙️
Local AI Assistant with file management, python scripting, and system commands!

---

## 🧤 Changelogs

- Support over WSL and bash
- Correct Google-style comments
- Dynamic system prompt based on Os and Terminal

## 🚧 To Do

- Toggle for sudo commands
- Retry N times when a tool fails
- Fix subprocess started by the model
- Allow argument to set default link and default model

---

## 🖥️ Supported OS

| OS      | Supported |
|---------|-----------|
| Windows | ❌        |
| WSL     | ✅        |
| Linux   | ✅        |
| Mac     | ❌        |

---

## 🧠 Ollama Setup

Make sure you got **Ollama** installed:

**Arch:**
```bash
sudo pacman -S ollama
```
**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```
**Windows:**
[Ollama Download Page](https://ollama.com/download/window)

---
Launch Ollama if it's not running:

```bash
ollama serve
```

Pull your model of choice (example):

```bash
ollama pull llama3.1:8b-instruct-q8_0
```

---

## 🐍 Python & Ollama Lib Setup

Make sure Python is installed, then set up your virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install ollama
```

---

## 🚀 Run CodePlex

Just launch it:

```bash
python codeplex.py
```

---

## ⚡ Quick Usage Tip

If you wanna make it easier, set up an alias like:

**Linux & WSL:**
```bash
nano ~/.bashrc
alias codeplex='source /path/to/venv/bin/activate && python /path/to/codeplex.py'
```

So you can just type `codeplex` and go.
