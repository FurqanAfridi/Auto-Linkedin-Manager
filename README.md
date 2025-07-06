# LinkedIn AI Automation Tool

## Overview
This Python program automates LinkedIn feed monitoring and engagement using AI-generated comments. It supports both OpenAI GPT and Google Gemini (via Gemini API) for generating comments on posts. The tool allows you to:
- Monitor your LinkedIn feed and automatically like and comment on posts.
- Choose between OpenAI GPT or Google Gemini for comment generation.
- Manage and configure API keys, prompts, and AI models via interactive menus.
- Run either natively on your system or inside a Docker container.

## Features
- **AI Comment Generation:** Uses either OpenAI GPT or Google Gemini to generate relevant comments for LinkedIn posts.
- **Configurable:** Easily switch between AI providers, change prompts, and update API keys.
- **Robust Automation:** Human-like delays, reliable selectors, and error handling for LinkedIn interactions.
- **Excel Integration:** Generate posts in bulk from Excel files using GPT.
- **Docker Support:** Run the tool in a containerized environment for consistency and isolation.

## How to Run (Without Docker)
1. **Install Python 3.8+**
2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
3. **Run the script:**
   ```powershell
   python "Monitor Feed.py"
   ```
4. **Follow the interactive menus** to configure API keys, prompts, and start LinkedIn automation.

## How to Run (With Docker)
1. **Ensure Docker Engine is running** (WSL2, Rancher Desktop, or Linux Docker, not Docker Desktop on Windows).
2. **Build the Docker image:**
   ```bash
   docker build -t linkedin-bot .
   ```
3. **Run the container:**
   ```bash
   docker run -it --rm \
     -v $(pwd)/config:/app/config \
     -v $(pwd)/Prompts:/app/Prompts \
     -v $(pwd)/files:/app/files \
     linkedin-bot
   ```
   - Adjust volume mounts as needed for your environment.
   - The script will prompt for configuration on first run.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Developer
**Name:** Muhammad Furqan Javed

