@echo off
set CUDA_VISIBLE_DEVICES=-1
set OLLAMA_CUDA=0
start /B ollama serve
echo Ollama started on CPU mode
