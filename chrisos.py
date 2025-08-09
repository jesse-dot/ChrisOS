# ChrisOS - A simple, text-based operating system simulation in Python.
# Version 1.0

import datetime
import time
import os
import shutil
import getpass
import calendar
from urllib.parse import urlparse

# Attempt to import the Tailscale library. This will be an optional feature.
try:
    import asyncio
    from tailscale import Tailscale

    TAILSCALE_ENABLED = True
except ImportError:
    TAILSCALE_ENABLED = False

# Attempt to import the ping3 library for external pings.
try:
    import ping3

    PING3_ENABLED = True
except ImportError:
    PING3_ENABLED = False

# Attempt to import the requests library for wget and weather.
try:
    import requests

    REQUESTS_ENABLED = True
except ImportError:
    REQUESTS_ENABLED = False


class ChrisOS:
    """
    This class encapsulates the functionality of ChrisOS, including
    the command loop, command handling, and a real file system integration.
    """
    VERSION = "1.0 (Stable)"

    def __init__(self, root_folder="chris_os_root"):
        """Initializes the OS, setting up paths and checking for first-time setup."""
        self.user = None
        self.root_path = os.path.abspath(root_folder)
        self.system_path = os.path.join(self.root_path, "system")
        self.home_path = os.path.join(self.root_path, "home")
        self.users_file = os.path.join(self.system_path, "users.txt")
        self.config_file = os.path.join(self.system_path, "config.txt")
        self.current_path = self.root_path
        self.command_history = []
        self.start_time = time.time()

        # Placeholders for Tailscale credentials
        self.tailscale_api_key = None
        self.tailscale_tailnet = None

        self.requires_login = True
        if not os.path.exists(self.root_path):
            self.first_time_setup()

        # Load any saved configuration
        self.load_config()

    def load_config(self):
        """Loads configuration from the system config file."""
        try:
            with open(self.config_file, "r") as f:
                for line in f:
                    if ":" in line:
                        key, value = line.strip().split(":", 1)
                        if key == "tailscale_tailnet":
                            self.tailscale_tailnet = value
                        elif key == "tailscale_api_key":
                            self.tailscale_api_key = value
        except FileNotFoundError:
            pass

    def save_config(self):
        """Saves the current configuration to the system config file."""
        print("Saving Tailscale credentials...")
        with open(self.config_file, "w") as f:
            if self.tailscale_tailnet:
                f.write(f"tailscale_tailnet:{self.tailscale_tailnet}\n")
            if self.tailscale_api_key:
                f.write(f"tailscale_api_key:{self.tailscale_api_key}\n")
        print("Credentials saved.")

    def first_time_setup(self):
        """Guides the user through creating the first admin account and logs them in."""
        print("--- ChrisOS First-Time Setup ---")
        username = input("Enter a username for the admin: ").strip()
        password = getpass.getpass("Enter a password for the admin: ")

        print(f"\nCreating OS file structure at: {self.root_path}")
        os.makedirs(self.system_path)
        user_home_dir = os.path.join(self.home_path, username)
        os.makedirs(user_home_dir)

        with open(self.users_file, "w") as f:
            f.write(f"{username}:{password}\n")

        self.user = username
        self.current_path = user_home_dir
        self.requires_login = False
        print(f"\nSetup complete. Welcome, {self.user}!")

    def login(self):
        """Handles the user login process."""
        print("--- ChrisOS Login ---")
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ").strip()

        try:
            with open(self.users_file, "r") as f:
                for line in f:
                    stored_user, stored_pass = line.strip().split(":", 1)
                    if username == stored_user and password == stored_pass:
                        self.user = username
                        user_home_dir = os.path.join(self.home_path, self.user)
                        if not os.path.exists(user_home_dir):
                            os.makedirs(user_home_dir)
                        self.current_path = user_home_dir
                        return True
        except FileNotFoundError:
            print("Error: users.txt not found. The OS might be corrupted.")
            return False

        print("\nInvalid username or password.")
        return False

    def get_relative_path(self):
        """Returns the current path relative to the OS root, using ~ for home."""
        user_home_dir = os.path.join(self.home_path, self.user)
        if self.current_path == user_home_dir: return "~"
        if self.current_path.startswith(user_home_dir):
            return "~/" + os.path.relpath(self.current_path, user_home_dir).replace("\\", "/")
        if self.current_path == self.root_path: return "/"
        return "/" + os.path.relpath(self.current_path, self.root_path).replace("\\", "/")

    def print_help(self):
        """Prints a list of all available commands."""
        print("\nChrisOS Command List (v" + self.VERSION + "):")
        print("  --- System ---")
        print("  help                - Shows this help message.")
        print("  sysinfo             - Displays system information.")
        print("  neofetch            - Shows a fancy system summary.")
        print("  history             - Shows command history.")
        print("  clear               - Clears the terminal screen.")
        print("  logout              - Logs out the current user.")
        print("  shutdown            - Shuts down ChrisOS.")
        print("\n  --- User ---")
        print("  whoami              - Shows the current user.")
        print("  passwd              - Changes your password.")
        print("  useradd             - Adds a new user.")
        print("\n  --- File & Directory ---")
        print("  ls / dir            - Lists files and directories.")
        print("  cd [dir]            - Changes directory ('~' for home).")
        print("  pwd                 - Shows the current working directory.")
        print("  cat [file]          - Displays the content of a file.")
        print("  edit [file]         - A simple text editor.")
        print("  grep [pattern] [file] - Searches for a pattern within a file.")
        print("  cp [src] [dest]     - Copies a file.")
        print("  mv [src] [dest]     - Moves or renames a file/directory.")
        print("  mkdir [name]        - Creates a new directory.")
        print("  touch [name]        - Creates a new empty file.")
        print("  rm [file]           - Deletes a file.")
        print("  rmdir [dir]         - Deletes an empty directory.")
        print("  find [name]         - Searches for a file in the current directory.")
        print("\n  --- Networking ---")
        print("  ts-status           - Shows the status of your Tailscale network (tailnet).")
        print("  ping [hostname]     - Pings a device on your tailnet or the internet.")
        print("  wget [url]          - Downloads a file from a URL.")
        print("\n  --- Applications ---")
        print("  weather [location]  - Shows the weather forecast for a location.")
        print("  run [file.chr]      - Executes a ChrisOS program file.")
        print("  calc [expression]   - A simple calculator.")
        print("  cal                 - Displays a calendar of the current month.")
        print("  time                - Displays the current time.")
        print("  date                - Displays the current date.")
        print("-" * 20)

    async def get_tailscale_status(self):
        """Async function to fetch and display Tailscale device status."""
        credentials_were_missing = not (self.tailscale_api_key and self.tailscale_tailnet)
        if credentials_were_missing:
            print("--- Tailscale Setup ---")
            print("Please provide your Tailscale information. It will be saved for future sessions.")
            self.tailscale_tailnet = input("Enter your tailnet name (e.g., example.com or smiley-cat.ts.net): ").strip()
            self.tailscale_api_key = getpass.getpass("Enter your Tailscale API key (tskey-...): ")

        print("\nConnecting to Tailscale API...")
        try:
            async with Tailscale(tailnet=self.tailscale_tailnet, api_key=self.tailscale_api_key) as tailscale:
                devices = await tailscale.devices()

                if credentials_were_missing:
                    self.save_config()

                print("--- Tailscale Devices ---")
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                for device_id, device in devices.items():
                    time_since_seen = now_utc - device.last_seen
                    status = "Online" if time_since_seen < datetime.timedelta(minutes=5) else "Offline"
                    ipv4 = device.addresses[0] if device.addresses else "N/A"
                    print(f"  - {device.hostname:<20} {str(ipv4):<15} {status}")
        except Exception as e:
            print("\nError: Could not connect to the Tailscale API.")
            print("This is often caused by an invalid Tailnet name or API key.")
            print(f"\n--- DEBUG INFO: {type(e).__name__}: {e} ---")
            self.tailscale_api_key = None
            self.tailscale_tailnet = None

    def ping_external(self, hostname):
        """Pings an external host on the public internet."""
        if not PING3_ENABLED:
            print("Error: The 'ping3' library is not installed on the host system.")
            print("Please run 'pip install ping3' to enable this feature.")
            return

        print(f"\nPinging {hostname}...")
        try:
            for i in range(4):
                delay = ping3.ping(hostname, unit='s')
                if delay is False:
                    print("Request timed out.")
                elif delay is None:
                    print(f"Error: Host '{hostname}' unknown.")
                    break
                else:
                    latency_ms = round(delay * 1000, 2)
                    print(f"Reply from {hostname}: time={latency_ms}ms")
                time.sleep(1)
        except Exception as e:
            if "permission denied" in str(e).lower() or "root" in str(e).lower():
                print("\nError: Permission denied. On some systems, ping requires administrator privileges.")
            else:
                print(f"An error occurred during ping: {e}")

    async def smart_ping(self, hostname):
        """Checks if a host is on the tailnet and pings it, otherwise pings the public internet."""
        target_device = None
        if TAILSCALE_ENABLED and self.tailscale_api_key and self.tailscale_tailnet:
            try:
                async with Tailscale(tailnet=self.tailscale_tailnet, api_key=self.tailscale_api_key) as tailscale:
                    devices = await tailscale.devices()
                    for device_id, device in devices.items():
                        if device.hostname.lower() == hostname.lower():
                            target_device = device
                            break
            except Exception:
                pass  # Ignore API errors, we'll just fall back to public ping.

        if target_device:
            # It's a Tailscale device, use the Tailscale ping.
            print(f"\nPinging Tailscale device {target_device.hostname} [{target_device.addresses[0]}]...")
            for i in range(4):
                try:
                    ping_result = await target_device.ping()
                    latency_ms = round(ping_result.latency_seconds * 1000, 2)
                    print(f"Reply from {target_device.addresses[0]}: time={latency_ms}ms")
                    await asyncio.sleep(1)
                except Exception:
                    print("Request timed out.")
        else:
            # Not a Tailscale device, so try pinging the public internet.
            # We run the synchronous ping_external in an executor to avoid blocking.
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.ping_external, hostname)

    def run(self):
        """The main loop for the operating system. Returns 'LOGOUT' or 'SHUTDOWN'."""
        print("=" * 40)
        print(f"Welcome to ChrisOS v{self.VERSION}! Logged in as: {self.user}")
        print("Type 'help' to see a list of commands.")
        print("=" * 40)

        while True:
            prompt = f"\nChrisOS ({self.user}@{self.get_relative_path()})> "
            command_input = input(prompt).strip()

            if not command_input: continue
            self.command_history.append(command_input)

            parts = command_input.split()
            command = parts[0].lower()
            args = parts[1:]

            try:
                # --- SYSTEM COMMANDS ---
                if command == "shutdown": return "SHUTDOWN"
                if command == "logout": return "LOGOUT"
                if command == "help":
                    self.print_help()
                elif command == "clear":
                    os.system('cls' if os.name == 'nt' else 'clear')
                elif command == "history":
                    for i, cmd in enumerate(self.command_history, 1):
                        print(f"  {i}: {cmd}")
                elif command == "sysinfo":
                    uptime = str(datetime.timedelta(seconds=int(time.time() - self.start_time)))
                    print(f"ChrisOS Version: {self.VERSION}")
                    print(f"System Uptime: {uptime}")
                    print(f"Root Path: {self.root_path}")
                elif command == "neofetch":
                    uptime = str(datetime.timedelta(seconds=int(time.time() - self.start_time)))
                    print("      ___           ___           ___     ")
                    print("     /  /\\         /  /\\         /  /\\    ")
                    print("    /  /:/_       /  /::\\       /  /::\\   ")
                    print("   /  /:/ /\\     /  /:/\\:\\     /  /:/\\:\\  ")
                    print("  /  /:/ /::\\   /  /:/~/::\\   /  /:/  \\:\\ ")
                    print(" /__/:/ /:/\\:\\ /__/:/ /:/\\:\\ /__/:/ \\__\\:\\")
                    print(" \\  \\:\\/:/~/:/ \\  \\:\\/:/__\\/ \\  \\:\\ /  /:/")
                    print("  \\  \\::/ /:/   \\  \\::/       \\  \\:\\  /:/ ")
                    print("   \\__\\/ /:/     \\  \\:\\        \\  \\:\\/:/  ")
                    print("     /__/:/       \\  \\:\\        \\  \\::/   ")
                    print("     \\__\\/         \\__\\/         \\__\\/    ")
                    print("-" * 30)
                    print(f"  User:       {self.user}")
                    print(f"  OS:         ChrisOS {self.VERSION}")
                    print(f"  Uptime:     {uptime}")
                    print(f"  Date:       {datetime.datetime.now().strftime('%Y-%m-%d')}")
                    print("-" * 30)

                # --- USER COMMANDS ---
                elif command == "whoami":
                    print(self.user)
                elif command == "useradd":
                    new_user = input("Enter new username: ").strip()
                    new_pass = getpass.getpass("Enter new password: ").strip()
                    if new_user and new_pass:
                        with open(self.users_file, "a") as f: f.write(f"{new_user}:{new_pass}\n")
                        os.makedirs(os.path.join(self.home_path, new_user), exist_ok=True)
                        print(f"User '{new_user}' created.")
                elif command == "passwd":
                    old_pass = getpass.getpass("Current password: ")
                    with open(self.users_file, "r") as f:
                        users = f.readlines()
                    user_found = False
                    for i, line in enumerate(users):
                        stored_user, stored_pass = line.strip().split(":", 1)
                        if self.user == stored_user and old_pass == stored_pass:
                            user_found = True
                            new_pass1 = getpass.getpass("New password: ")
                            new_pass2 = getpass.getpass("Retype new password: ")
                            if new_pass1 == new_pass2:
                                users[i] = f"{self.user}:{new_pass1}\n"
                                with open(self.users_file, "w") as f:
                                    f.writelines(users)
                                print("Password updated successfully.")
                            else:
                                print("Passwords do not match.")
                            break
                    if not user_found: print("Incorrect password.")

                # --- FILE & DIR COMMANDS ---
                elif command in ["ls", "dir"]:
                    print("Directory listing:")
                    items = os.listdir(self.current_path)
                    if not items: print("(empty)")
                    for item in sorted(items):
                        item_path = os.path.join(self.current_path, item)
                        item_type = "[DIR]" if os.path.isdir(item_path) else "[FILE]"
                        print(f"  {item_type:<6} {item}")
                elif command == "pwd":
                    print(self.get_relative_path())
                elif command == "cd":
                    target = args[0] if args else "~"
                    if target == "~":
                        self.current_path = os.path.join(self.home_path, self.user)
                    else:
                        new_path = os.path.abspath(os.path.join(self.current_path, target))
                        if not new_path.startswith(self.root_path):
                            print("Error: Cannot cd outside OS root.")
                        elif os.path.isdir(new_path):
                            self.current_path = new_path
                        else:
                            print(f"Error: Directory '{target}' not found.")
                elif command == "cat":
                    if not args:
                        print("Usage: cat [filename]")
                    else:
                        file_path = os.path.join(self.current_path, args[0])
                        if os.path.isfile(file_path):
                            with open(file_path, 'r') as f:
                                print(f.read(), end="")
                        else:
                            print(f"Error: File '{args[0]}' not found.")
                elif command == "edit":
                    if not args:
                        print("Usage: edit [filename]")
                    else:
                        file_path = os.path.join(self.current_path, args[0])
                        print(f"--- Editing {args[0]} --- (Type ':wq' on a new line to save and exit)")
                        lines = []
                        if os.path.exists(file_path):
                            with open(file_path, 'r') as f:
                                lines = [line.rstrip('\n') for line in f.readlines()]
                            for line in lines: print(line)

                        while True:
                            line = input()
                            if line == ':wq': break
                            lines.append(line)
                        with open(file_path, 'w') as f:
                            f.write('\n'.join(lines))
                        print("File saved.")
                elif command == "grep":
                    if len(args) != 2:
                        print("Usage: grep [pattern] [filename]")
                    else:
                        pattern = args[0]
                        filename = args[1]
                        file_path = os.path.join(self.current_path, filename)
                        if os.path.isfile(file_path):
                            found_match = False
                            with open(file_path, 'r') as f:
                                for i, line in enumerate(f, 1):
                                    if pattern in line:
                                        print(f"{i}: {line.strip()}")
                                        found_match = True
                            if not found_match:
                                print(f"No matches for '{pattern}' found in '{filename}'.")
                        else:
                            print(f"Error: File '{filename}' not found.")
                elif command == "cp":
                    if len(args) != 2:
                        print("Usage: cp [source] [destination]")
                    else:
                        src = os.path.join(self.current_path, args[0])
                        dest = os.path.join(self.current_path, args[1])
                        if os.path.isfile(src):
                            shutil.copy(src, dest)
                            print(f"Copied '{args[0]}' to '{args[1]}'.")
                        else:
                            print(f"Error: Source file '{args[0]}' not found.")
                elif command == "mv":
                    if len(args) != 2:
                        print("Usage: mv [source] [destination]")
                    else:
                        src = os.path.join(self.current_path, args[0])
                        dest = os.path.join(self.current_path, args[1])
                        shutil.move(src, dest)
                        print(f"Moved '{args[0]}' to '{args[1]}'.")
                elif command == "mkdir":
                    if not args:
                        print("Usage: mkdir [dirname]")
                    else:
                        os.mkdir(os.path.join(self.current_path, args[0]))
                        print(f"Directory '{args[0]}' created.")
                elif command == "touch":
                    if not args:
                        print("Usage: touch [filename]")
                    else:
                        open(os.path.join(self.current_path, args[0]), 'a').close()
                        print(f"File '{args[0]}' created.")
                elif command == "rm":
                    if not args:
                        print("Usage: rm [filename]")
                    else:
                        file_path = os.path.join(self.current_path, args[0])
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            print(f"File '{args[0]}' removed.")
                        else:
                            print(f"Error: '{args[0]}' is not a file.")
                elif command == "rmdir":
                    if not args:
                        print("Usage: rmdir [dirname]")
                    else:
                        dir_path = os.path.join(self.current_path, args[0])
                        if os.path.isdir(dir_path):
                            os.rmdir(dir_path)
                            print(f"Directory '{args[0]}' removed.")
                        else:
                            print(f"Error: '{args[0]}' is not a directory.")
                elif command == "find":
                    if not args:
                        print("Usage: find [filename]")
                    else:
                        found = False
                        for root, dirs, files in os.walk(self.current_path):
                            if args[0] in files:
                                found = True
                                result_path = os.path.join(root, args[0])
                                print(os.path.relpath(result_path, self.current_path))
                        if not found: print(f"File '{args[0]}' not found.")

                # --- NETWORKING COMMANDS ---
                elif command == "ts-status":
                    if not TAILSCALE_ENABLED:
                        print("Error: The 'tailscale' library is not installed on the host system.")
                        print("Please run 'pip install tailscale' to enable this feature.")
                    else:
                        asyncio.run(self.get_tailscale_status())
                elif command == "ping":
                    if not args:
                        print("Usage: ping [hostname]")
                    else:
                        asyncio.run(self.smart_ping(args[0]))
                elif command == "wget":
                    if not REQUESTS_ENABLED:
                        print("Error: The 'requests' library is not installed on the host system.")
                        print("Please run 'pip install requests' to enable this feature.")
                    elif not args:
                        print("Usage: wget [url]")
                    else:
                        url = args[0]
                        try:
                            print(f"Connecting to {url}...")
                            response = requests.get(url, allow_redirects=True)
                            response.raise_for_status()  # Raises an error for bad status codes (4xx or 5xx)

                            parsed_url = urlparse(url)
                            filename = os.path.basename(parsed_url.path)
                            if not filename:
                                filename = "index.html"

                            file_path = os.path.join(self.current_path, filename)
                            with open(file_path, 'wb') as f:
                                f.write(response.content)

                            size = len(response.content)
                            print(f"Saved to '{filename}' ({size} bytes).")

                        except requests.exceptions.RequestException as e:
                            print(f"Error during download: {e}")

                # --- APPLICATIONS ---
                elif command == "weather":
                    if not REQUESTS_ENABLED:
                        print("Error: The 'requests' library is not installed on the host system.")
                    else:
                        location = " ".join(args) if args else "Baltimore"
                        url = f"https://wttr.in/{location}?format=3"
                        try:
                            print(f"Fetching weather for {location}...")
                            response = requests.get(url)
                            response.raise_for_status()
                            print(response.text)
                        except requests.exceptions.RequestException as e:
                            print(f"Error fetching weather: {e}")
                elif command == "run":
                    if not args or not args[0].endswith(".chr"):
                        print("Error: Must be a .chr file.")
                    else:
                        file_path = os.path.join(self.current_path, args[0])
                        if os.path.isfile(file_path):
                            print(f"--- Executing {args[0]} ---")
                            with open(file_path, 'r') as f:
                                exec(f.read(), {'__name__': '__main__'})
                            print(f"--- Finished executing {args[0]} ---")
                        else:
                            print(f"Error: Program file '{args[0]}' not found.")
                elif command == "calc":
                    if not args:
                        print("Usage: calc [expression]")
                    else:
                        expression = "".join(args)
                        allowed_chars = "0123456789+-*/(). "
                        if all(char in allowed_chars for char in expression):
                            try:
                                result = eval(expression)
                                print(f"Result: {result}")
                            except Exception as e:
                                print(f"Error in calculation: {e}")
                        else:
                            print(
                                "Error: Invalid characters in expression. Only numbers and operators (+-*/) are allowed.")
                elif command == "cal":
                    now = datetime.datetime.now()
                    print(calendar.month(now.year, now.month))
                elif command == "time":
                    print(datetime.datetime.now().strftime('%H:%M:%S'))
                elif command == "date":
                    print(datetime.datetime.now().strftime('%Y-%m-%d'))
                else:
                    print(f"Error: Command '{command}' not recognized.")
            except Exception as e:
                print(f"An error occurred: {e}")


# --- Main execution ---
if __name__ == "__main__":
    while True:
        my_os = ChrisOS()

        login_successful = not my_os.requires_login
        if my_os.requires_login:
            login_successful = my_os.login()

        if login_successful:
            action = my_os.run()
            if action == "SHUTDOWN":
                print("Shutting down ChrisOS...")
                break
            elif action == "LOGOUT":
                print("Logging out...")
                continue
        else:
            print("Login failed. Exiting ChrisOS.")
            break
