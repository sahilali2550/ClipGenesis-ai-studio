# ClipGenesis-Extended — Zero Budget Setup Guide

## 🚀 Step-by-Step Instructions (Raat Ko Karna)

### ✅ Step 1: Python 3.10.11 Install Karo (GUI Se)
1. **Yeh link kholo:** [https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe](https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe)
2. **Download hone ke baad:**
   - **Double-click** karo (installer khulega).
   - ✅ **"Add Python to PATH"** check karo (zaroori hai).
   - ✅ **"Install for all users"** select karo (recommended).
   - **Install** click karo.
3. **Installation complete hone ke baad PowerShell restart karo.**

### ✅ Step 2: Python Verify Karo
```powershell
python --version
```
- **Expected Output:** `Python 3.10.11`

### ✅ Step 3: ClipGenesis-Extended Setup Complete Karo
```powershell
cd C:\OpenClaw\.openclaw\.openclaw\workspace\ClipGenesis-Extended
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### ✅ Step 4: Chatterbox TTS Install Karo (Free Voice Cloning)
```powershell
git clone https://github.com/resemble-ai/chatterbox.git
cd chatterbox && pip install -e . && cd ..
```

### ✅ Step 5: Run ClipGenesis-Extended
```powershell
python app.py
```

### 🎯 Tips
- **Agar `pip install -r requirements.txt` me error aaye**, to yeh try karo:
  ```powershell
  pip install --upgrade pip
  pip install -r requirements.txt
  ```
- **Agar `git clone` me error aaye**, to Git install karo: [https://git-scm.com/download/win](https://git-scm.com/download/win)