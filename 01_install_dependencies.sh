#!/bin/bash

pip install playwright
pip install tqdm
pip install langchain langchain-ollama
playwright install
sudo apt update
sudo apt install -y xvfb
curl -fsSL https://ollama.com/install.sh | sh