#!/usr/bin/env python3
#########
# GitHub Repository Sync Script
# Author: Henry Standing <henry.standing@gmail.com>
# Version: v1.2, 2025-02-04
# Source: https://github.com/NoHomeLacey/dotfiles
#########

"""
GitHub Repository Synchronization Script

This script automatically manages GitHub repositories by:
  - Installing necessary dependencies (Git, GitHub CLI).
  - Ensuring GitHub authentication via `gh auth login` and `ssh -T git@github.com`.
  - Cloning missing repositories and pulling the latest changes for existing ones.
  - Providing interactive options for committing and pushing changes before pulling.

Options:
  - No options required; the script automatically detects OS and installs dependencies.

Supported Platforms:
  - macOS (Homebrew)
  - Linux (APT, DNF, YUM)
  - Windows (winget, Chocolatey)

Before running this script:
  1. Ensure GitHub CLI is installed and authenticated:
     $ gh auth login
  2. Verify SSH access:
     $ ssh -T git@github.com
  3. Run the script:
     $ python3 git-repo-manager.py
"""

import os
import subprocess
import sys

# Define the directory where repositories will be stored
CLONE_DIR = os.path.expanduser("~/git")

###############################################################################
# Utility Functions                                                           #
###############################################################################

def run_command(cmd, check=False, capture_output=False):
    """Executes a shell command safely."""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=check)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {cmd}\nError: {e}")
        sys.exit(1)

def detect_os():
    """Detects the operating system and package manager."""
    if sys.platform.startswith("linux"):
        if os.path.exists("/usr/bin/apt"):
            return "linux-apt"
        elif os.path.exists("/usr/bin/dnf"):
            return "linux-dnf"
        elif os.path.exists("/usr/bin/yum"):
            return "linux-yum"
        else:
            return "linux-unknown"
    elif sys.platform == "darwin":
        return "macos"
    elif sys.platform in ["win32", "cygwin"]:
        return "windows"
    else:
        return "unknown"

###############################################################################
# Dependency Management                                                       #
###############################################################################

def install_package(package):
    """Installs a package using the appropriate package manager."""
    os_type = detect_os()
    print(f"🔧 Installing {package}...")

    if os_type == "linux-apt":
        run_command(f"sudo apt update -y && sudo apt install -y {package}")
    elif os_type == "linux-dnf":
        run_command(f"sudo dnf install -y {package}")
    elif os_type == "linux-yum":
        run_command(f"sudo yum install -y {package}")
    elif os_type == "macos":
        run_command(f"brew install {package}")
    elif os_type == "windows":
        if package == "git":
            run_command("winget install --id Git.Git --silent") or run_command("choco install git -y")
        elif package == "gh":
            run_command("winget install --id GitHub.cli --silent") or run_command("choco install gh -y")
    else:
        print(f"⚠️ Unsupported OS: {os_type}. Install {package} manually.")
        sys.exit(1)

def ensure_dependencies():
    """Ensures Git and GitHub CLI are installed."""
    for package in ["git", "gh"]:
        if subprocess.call(["which", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            install_package(package)
        else:
            print(f"✅ {package} is already installed.")

###############################################################################
# Authentication & Setup                                                      #
###############################################################################

def authenticate_github():
    """Ensures the user is authenticated with GitHub CLI."""
    if subprocess.call(["gh", "auth", "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
        print("🔑 GitHub CLI authentication required.")
        run_command("gh auth login")
    else:
        print("✅ GitHub authentication is already set up.")

def check_ssh_access():
    """Verifies SSH authentication with GitHub and correctly handles expected output."""
    print("🔍 Checking SSH access to GitHub...")
    
    result = subprocess.run(["ssh", "-T", "git@github.com"], capture_output=True, text=True)
    ssh_output = (result.stdout + result.stderr).strip()
    
    if "successfully authenticated" in ssh_output or "does not provide shell access" in ssh_output:
        print("✅ SSH authentication with GitHub is working.")
    else:
        print(f"⚠️ SSH authentication failed. Full output:\n{ssh_output}")
        sys.exit(1)

def get_github_user():
    """Retrieves the GitHub username from GitHub CLI."""
    username = run_command("gh api user --jq .login", capture_output=True)
    return username if username else input("Enter your GitHub username: ").strip()

###############################################################################
# Repository Synchronization                                                  #
###############################################################################

def fetch_repos(username):
    """Fetches all repositories from GitHub."""
    print(f"📡 Fetching repository list for {username}...")
    repo_data = run_command(f"gh repo list {username} --json name,url --jq '.[] | \"\(.name) \(.url)\"'", capture_output=True)

    if not repo_data:
        print("❌ No repositories found or API call failed.")
        return []

    return [line.strip().split() for line in repo_data.split("\n")]

def clone_or_update_repos(repos):
    """Clones missing repositories, commits & pushes local changes interactively, and updates existing ones."""
    os.makedirs(CLONE_DIR, exist_ok=True)
    os.chdir(CLONE_DIR)
    print(f"📁 Using clone directory: {CLONE_DIR}")

    run_command("git config --global pull.ff only")  # Set default pull strategy

    for repo_name, repo_url in repos:
        repo_path = os.path.join(CLONE_DIR, repo_name)

        if os.path.exists(repo_path) and os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, ".git")):
            print(f"\n🔄 Updating existing repo: {repo_name}")
            os.chdir(repo_path)

            # ✅ Check for uncommitted changes
            changes = run_command("git status --porcelain", capture_output=True)
            if changes:
                print(f"\n📝 Uncommitted changes detected in {repo_name}:")
                print(changes)  

                if input(f"Commit all changes in {repo_name}? (y/n): ").strip().lower() == "y":
                    run_command("git add .")
                    run_command(f'git commit -m "Auto-commit before pull: {repo_name}"')
                    run_command("git push origin $(git rev-parse --abbrev-ref HEAD)", check=True)

            current_branch = run_command("git rev-parse --abbrev-ref HEAD", capture_output=True)
            if "fatal" not in current_branch:
                run_command(f"git pull origin {current_branch}", check=True)

        else:
            print(f"🚀 Cloning new repository: {repo_name}")
            run_command(f"git clone {repo_url} {repo_path}")

    print("🎉 All repositories are synced!")

###############################################################################
# Main Execution                                                              #
###############################################################################

def main():
    """Main script execution."""
    print("🔧 Setting up Git & Syncing GitHub Repositories...")

    ensure_dependencies()
    authenticate_github()
    check_ssh_access()

    username = get_github_user()
    print(f"👤 Logged in as: {username}")

    repos = fetch_repos(username)
    if repos:
        clone_or_update_repos(repos)
    else:
        print("❌ No repositories found. Exiting.")

if __name__ == "__main__":
    main()