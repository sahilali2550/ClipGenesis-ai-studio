@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp0"
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32
set CUDNN_LOGINFO_DBG=0

rem Add cuDNN to path if conda env style bin exists in venv
if exist ".venv\Lib\site-packages\nvidia\cudnn\bin" (
    set "PATH=%~dp0.venv\Lib\site-packages\nvidia\cudnn\bin;%PATH%"
)

.venv\Scripts\python.exe main.py
