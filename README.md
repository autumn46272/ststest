# Slay the Spire Python CLI Bot

This is a rule-based automated bot for *Slay the Spire*, designed to interface with the game via the [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod). It reads the game state from standard input (`stdin`) and sends control commands to standard output (`stdout`).

## Features

- **Bug-Free State Extraction**: Parses both root-level metadata and nested `game_state` fields correctly.
- **Ready Handshake**: Sends the initial `"ready"` signal on startup to initiate communication with `CommunicationMod`.
- **Combat Logic**:
  - Automatically calculates incoming enemy damage (including multi-attacks).
  - Prioritizes playing `"POWER"` cards first to set up permanent combat buffs.
  - Plays defensive `"SKILL"` (block) cards when threatened by incoming damage.
  - Plays `"ATTACK"` cards targeting the alive enemy with the lowest HP to defeat them quickly.
  - Automatically ends the turn when no playable cards remain.
- **Non-Combat Screen Navigation**:
  - Automatically picks card rewards, chooses campfire options, and navigates events by choosing the first available option.
  - Avoids getting stuck in shop screens by detecting and selecting the `"leave"` / `"exit"` options.
  - Employs fallback commands (`proceed`, `confirm`, `cancel`, `leave`) when no explicit choice options exist.

## Setup Instructions

1. **Install CommunicationMod**:
   - Download and install `CommunicationMod` via the ModTheSpire workshop or GitHub repository.
   - Make sure you also have `ModTheSpire` and `BaseMod` installed.

2. **Configure Mod Command**:
   - Locate the configuration file on your machine:
     - **Windows**: `%LOCALAPPDATA%\ModTheSpire\CommunicationMod\config.properties`
   - Open `config.properties` and edit the `command` property to point to the [bot.py](bot.py) script:
     ```properties
     command=python C:/Users/micro/OneDrive/Documents/Coding/bot.py
     ```
     *(Note: Ensure you use forward slashes `/` in the file path, as Java properties treat backslashes `\` as escape characters.)*

3. **Run Slay the Spire**:
   - Launch ModTheSpire, enable `BaseMod` and `CommunicationMod`, and start the game. The bot will automatically start a run as the Ironclad.

---

## Troubleshooting: Stuck in the Main Menu?

If you launch Slay the Spire with mods enabled and find yourself stuck in the main menu, this is **not** supposed to happen. When working correctly, the bot should automatically command the game to start a run. If it remains stuck, check the following common causes:

### 1. Escape Characters in `config.properties` (Most Common)
In Java `.properties` files, a backslash (`\`) is treated as an escape character. If you configured the path as:
`command=python C:\Users\micro\OneDrive\Documents\Coding\bot.py`
The mod will fail to parse the path and cannot launch the bot.
* **Fix**: Use forward slashes `/` instead:
  `command=python C:/Users/micro/OneDrive/Documents/Coding/bot.py`
  Or escape the backslashes:
  `command=python C:\\Users\\micro\\OneDrive\\Documents\\Coding\\bot.py`

### 2. Python is not in the System PATH
If `python` cannot be executed globally, `ModTheSpire` will fail to launch the process.
* **Verify**: Open a standard terminal (Command Prompt or PowerShell) and type `python --version`. If it is not recognized, you must add Python to your system environment variables.
* **Fix**: Alternatively, specify the absolute path to your Python executable in the configuration:
  `command=C:/Users/micro/AppData/Local/Programs/Python/Python3x/python.exe C:/Users/micro/OneDrive/Documents/Coding/bot.py`

### 3. Check the Mod Error Logs
When `CommunicationMod` attempts to launch the script, it redirects the bot's stderr to an error log file.
* **Locate**: Look for the log file at `%LOCALAPPDATA%\ModTheSpire\CommunicationMod\communication_mod_errors.log` (or within your Steam game directory under `mods/CommunicationMod/`).
* **Inspect**: Open the file. It will show any Python traceback errors, syntax errors, or launch failures.
