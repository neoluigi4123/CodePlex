# CodePlex ⚙️
Local AI Assistant with file management, python scripting, and system commands!

---

## 🚧 To Do

- Toggle for sudo commands
- Retry N times when a tool fails
- Fix subprocess started by the model
- Allow argument to set default link and default model
- Port to Windows

---

## 🖥️ Supported OS

| OS      | Supported |
|---------|-----------|
| Windows | ❌        |
| Linux   | ✅        |
| Mac     | ❌        |

---

## 🧠 Ollama Setup

Make sure you got **Ollama** installed:

```bash
sudo pacman -S ollama
````

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

```bash
alias codeplex='source /path/to/venv/bin/activate && python /path/to/codeplex.py'
```

So you can just type `codeplex` and go.
