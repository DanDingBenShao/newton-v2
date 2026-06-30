#!/usr/bin/env python3
"""
Newton-X CLI — single entry point for the entire system.

Usage:
  newton init     Initialize Newton-X (create config, set API key)
  newton start    Launch System 2 daemon + monitor (visible terminal)
  newton agent    Launch standalone agent (polls for tasks)
  newton all      Launch both daemon + agent
  newton test     Run extended test matrix
  newton demo     Run realistic 3-phase scenario
"""

import sys, os, subprocess

CORE_DIR = os.path.dirname(os.path.abspath(__file__))


def check_key():
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Error: DEEPSEEK_API_KEY environment variable not set.")
        print("  export DEEPSEEK_API_KEY=your-key-here")
        sys.exit(1)


def launch_terminal(script: str):
    """Launch a Python script in a visible terminal window."""
    if sys.platform == "win32":
        subprocess.Popen(
            ["cmd", "/c", "start", "Newton-X", "cmd", "/k",
             f'chcp 65001 >nul && cd /d "{CORE_DIR}" && python {script}'],
            shell=False,
        )
    else:
        subprocess.Popen(
            ["x-terminal-emulator", "-e", f"python {os.path.join(CORE_DIR, script)}"],
        )


def cmd_start():
    """Launch the System 2 daemon + monitor."""
    launch_terminal("system2_daemon.py")
    print("System 2 Monitor launched in new terminal.")


def cmd_agent():
    """Launch the standalone agent."""
    check_key()
    launch_terminal("standalone_agent.py")
    print("Agent launched in new terminal. Write tasks to ~/.newton-x/newton_task.jsonl")


def cmd_all():
    """Launch both daemon and agent."""
    cmd_start()
    import time; time.sleep(1)
    cmd_agent()


def cmd_init():
    """Initialize Newton-X: create config and directory structure."""
    from config import init_config, CONFIG_DIR
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        api_key = input("DeepSeek API Key (leave empty to set later): ").strip()
    init_config(api_key)
    print(f"  Config:   {CONFIG_DIR / 'config.json'}")
    print(f"  Streams:  {CONFIG_DIR}")
    print("  Ready. Run 'newton start' to launch the monitor.")


def cmd_test():
    """Run extended test matrix."""
    check_key()
    os.chdir(os.path.dirname(CORE_DIR))
    sys.path.insert(0, ".")
    from tests.extended_test import main
    main()


def cmd_demo():
    """Run realistic 3-phase scenario."""
    check_key()
    os.chdir(os.path.dirname(CORE_DIR))
    sys.path.insert(0, ".")
    from tests.realistic_scenario import main
    main()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    commands = {
        "init": cmd_init,
        "start": cmd_start,
        "agent": cmd_agent,
        "all": cmd_all,
        "test": cmd_test,
        "demo": cmd_demo,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)


if __name__ == "__main__":
    main()
