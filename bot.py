import sys
import json
import os
import subprocess
import datetime

# --- Logging Setup ---
# We write all logs to a file next to this script, then open a cmd.exe window
# that live-tails it. This works reliably no matter how the game launches us.

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_log.txt")

# Open the log file (overwrite on each new run so it stays readable)
_log_file = open(LOG_FILE, "w", encoding="utf-8", buffering=1)

def log(message):
    """Since stdout is used to talk to the game, we write logs to a file instead."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, file=_log_file, flush=True)

# Redirect Python's own stderr (tracebacks etc.) into the log file too
sys.stderr = _log_file

# Open a separate cmd.exe window that live-tails the log file using PowerShell.
# 'start' always creates a new window; Get-Content -Wait is the Windows equivalent of tail -f.
try:
    subprocess.Popen(
        [
            "cmd.exe", "/c", "start",
            "Slay the Spire Bot Logs",          # Window title
            "powershell", "-NoExit", "-Command",
            f"Get-Content -Wait '{LOG_FILE}'"
        ],
        close_fds=True
    )
except Exception as e:
    log(f"Could not open log window: {e}")

def send_command(command):
    """Sends a command to Slay the Spire and flushes the buffer."""
    log(f"Sending command: {command}")
    print(command, flush=True)

log("Bot script started. Sending ready handshake...")

# Initial handshake required by CommunicationMod to start receiving state updates
print("ready", flush=True)

# Main game loop
for line in sys.stdin:
    try:
        # Parse the JSON state sent by CommunicationMod (at root level)
        state_data = json.loads(line.strip())
        if not state_data:
            continue
        
        # Check if we are ready for a command
        if state_data.get("ready_for_command"):
            game_state = state_data.get("game_state", {})
            if not game_state:
                # Fallback if ready but nested game_state is missing
                send_command("proceed")
                continue
                
            screen_type = game_state.get("screen_type")
            log(f"Current Screen: {screen_type}")

            # Check if we are in combat (screen_type is "NONE" in combat)
            combat_state = game_state.get("combat_state")
            in_combat = (screen_type == "NONE") and (combat_state is not None)

            if in_combat:
                # Check if it's actually our turn to act
                turn_phase = game_state.get("screen_state", {}).get("turn_phase", "ACTION")
                if turn_phase == "ACTION":
                    hand = combat_state.get("hand", [])
                    monsters = combat_state.get("monsters", [])
                    
                    # Filter playable cards (1-indexed positions)
                    playable_cards = []
                    for idx, card in enumerate(hand):
                        if card.get("is_playable"):
                            playable_cards.append((idx + 1, card))
                    
                    if not playable_cards:
                        # End turn if no cards can be played
                        send_command("end")
                    else:
                        # Categorize playable cards for prioritisation
                        powers = [c for c in playable_cards if c[1].get("type") == "POWER"]
                        skills = [c for c in playable_cards if c[1].get("type") == "SKILL"]
                        attacks = [c for c in playable_cards if c[1].get("type") == "ATTACK"]
                        others = [c for c in playable_cards if c[1].get("type") not in ("POWER", "SKILL", "ATTACK")]
                        
                        # Get player block and compute incoming monster damage
                        player_block = game_state.get("player", {}).get("block", 0)
                        
                        incoming_damage = 0
                        for monster in monsters:
                            is_alive = monster.get("current_hp", 0) > 0 and not monster.get("is_gone", False) and not monster.get("half_dead", False)
                            if is_alive:
                                intent_dmg = monster.get("intent_damage", 0)
                                if intent_dmg > 0:
                                    multi = monster.get("intent_num_attacks", monster.get("intent_multi_amount", 1))
                                    if not isinstance(multi, int):
                                        multi = 1
                                    incoming_damage += intent_dmg * multi
                        
                        # Select best card to play based on priority heuristics:
                        # 1. Powers first (limit to setup buffs)
                        # 2. Defensive skills if we are taking damage and need block
                        # 3. Attacks to thin out or defeat enemies
                        # 4. Rest of skills/others
                        selected_card_info = None
                        if powers:
                            selected_card_info = powers[0]
                        elif skills and player_block < incoming_damage:
                            selected_card_info = skills[0]
                        elif attacks:
                            selected_card_info = attacks[0]
                        elif skills:
                            selected_card_info = skills[0]
                        else:
                            selected_card_info = others[0] if others else None
                        
                        if selected_card_info:
                            card_idx, card = selected_card_info
                            
                            # Check if the card requires targeting
                            if card.get("has_target"):
                                # Find the alive monster with the lowest HP
                                target_idx = None
                                min_hp = float('inf')
                                for idx, monster in enumerate(monsters):
                                    is_alive = monster.get("current_hp", 0) > 0 and not monster.get("is_gone", False) and not monster.get("half_dead", False)
                                    if is_alive:
                                        hp = monster.get("current_hp", 0)
                                        if hp < min_hp:
                                            min_hp = hp
                                            target_idx = idx
                                
                                if target_idx is not None:
                                    send_command(f"play {card_idx} {target_idx}")
                                else:
                                    send_command(f"play {card_idx}")
                            else:
                                send_command(f"play {card_idx}")
                        else:
                            send_command("end")
                else:
                    send_command("wait")
            
            elif screen_type == "MAIN_MENU":
                send_command("start ironclad")
            
            else:
                # Handle non-combat choice screens
                choice_list = state_data.get("choice_list", game_state.get("choice_list", []))
                if choice_list:
                    if screen_type == "SHOP_SCREEN":
                        # Look for an exit/leave choice to avoid buying loop
                        leave_idx = None
                        for idx, choice in enumerate(choice_list):
                            if "leave" in choice.lower() or "exit" in choice.lower():
                                leave_idx = idx
                                break
                        if leave_idx is not None:
                            send_command(f"choose {leave_idx}")
                        else:
                            send_command("choose 0")
                    else:
                        # Default to choosing the first reward or option
                        send_command("choose 0")
                else:
                    # If choice list is empty, fall back to buttons in available_commands
                    avail_cmds = state_data.get("available_commands", [])
                    if "proceed" in avail_cmds:
                        send_command("proceed")
                    elif "confirm" in avail_cmds:
                        send_command("confirm")
                    elif "cancel" in avail_cmds:
                        send_command("cancel")
                    elif "leave" in avail_cmds:
                        send_command("leave")
                    else:
                        send_command("proceed")
        else:
            # If the game isn't ready for a command, we wait
            send_command("wait")

    except Exception as e:
        log(f"Error parsing game state: {e}")
