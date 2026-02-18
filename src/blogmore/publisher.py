"""Git publishing functionality for blogmore."""

import shutil
import subprocess
import sys
from pathlib import Path


class PublishError(Exception):
    """Exception raised when publishing fails."""

    pass


def check_git_available() -> bool:
    """Check if git command is available in the PATH.

    Returns:
        True if git is available, False otherwise
    """
    return shutil.which("git") is not None


def check_is_git_repository(path: Path | None = None) -> bool:
    """Check if the given path is within a git repository.

    Args:
        path: Path to check (default: current working directory)

    Returns:
        True if path is in a git repository, False otherwise
    """
    if path is None:
        path = Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_git_root(path: Path | None = None) -> Path:
    """Get the root directory of the git repository.

    Args:
        path: Path within the repository (default: current working directory)

    Returns:
        Path to the git repository root

    Raises:
        PublishError: If not in a git repository
    """
    if path is None:
        path = Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            check=True,
            text=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise PublishError("Not in a git repository") from e


def publish_site(
    output_dir: Path,
    branch: str = "gh-pages",
    remote: str = "origin",
    working_dir: Path | None = None,
) -> None:
    """Publish the generated site to a git branch.

    This function:
    1. Checks that git is available
    2. Checks that we're in a git repository
    3. Creates/checks out the target branch
    4. Copies the output directory contents to the branch
    5. Commits the changes
    6. Pushes to the remote

    Args:
        output_dir: Directory containing the generated site
        branch: Git branch to publish to (default: gh-pages)
        remote: Git remote to push to (default: origin)
        working_dir: Working directory (default: current directory)

    Raises:
        PublishError: If any step of the publishing process fails
    """
    if working_dir is None:
        working_dir = Path.cwd()

    # Check git is available
    if not check_git_available():
        raise PublishError(
            "Git command not found. Please install git and ensure it's in your PATH."
        )

    # Check we're in a git repository
    if not check_is_git_repository(working_dir):
        raise PublishError(
            "Not in a git repository. Please run this command from within a git repository."
        )

    # Get git root
    git_root = get_git_root(working_dir)

    # Check that output directory exists and has content
    if not output_dir.exists():
        raise PublishError(
            f"Output directory not found: {output_dir}. Please build the site first."
        )

    if not any(output_dir.iterdir()):
        raise PublishError(
            f"Output directory is empty: {output_dir}. Please build the site first."
        )

    print(f"Publishing site to branch '{branch}' on remote '{remote}'...")

    # Save current branch/commit
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=git_root,
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            current_ref = result.stdout.strip()
        else:
            # Detached HEAD state
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=git_root,
                capture_output=True,
                check=True,
                text=True,
            )
            current_ref = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise PublishError(f"Failed to determine current git ref: {e}") from e

    try:
        # Check if the branch exists locally
        branch_check_result = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            cwd=git_root,
            capture_output=True,
            check=False,
        )
        branch_exists = branch_check_result.returncode == 0

        if branch_exists:
            # Checkout existing branch
            subprocess.run(
                ["git", "checkout", branch],
                cwd=git_root,
                check=True,
                capture_output=True,
            )
            print(f"Checked out existing branch '{branch}'")

            # Remove all files from the branch (except .git)
            subprocess.run(
                ["git", "rm", "-rf", "."],
                cwd=git_root,
                check=True,
                capture_output=True,
            )
        else:
            # Create orphan branch
            subprocess.run(
                ["git", "checkout", "--orphan", branch],
                cwd=git_root,
                check=True,
                capture_output=True,
            )
            print(f"Created new orphan branch '{branch}'")

            # Remove all files
            subprocess.run(
                ["git", "rm", "-rf", "."],
                cwd=git_root,
                check=False,
                capture_output=True,
            )

        # Copy all files from output directory to git root
        for item in output_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, git_root / item.name)
            elif item.is_dir():
                shutil.copytree(item, git_root / item.name, dirs_exist_ok=True)

        # Add all files
        subprocess.run(
            ["git", "add", "-A"],
            cwd=git_root,
            check=True,
            capture_output=True,
        )

        # Check if there are any changes to commit
        diff_result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=git_root,
            check=False,
        )

        if diff_result.returncode == 0:
            print("No changes to publish")
        else:
            # Commit the changes
            subprocess.run(
                ["git", "commit", "-m", "Publish site"],
                cwd=git_root,
                check=True,
                capture_output=True,
            )
            print("Changes committed")

            # Push to remote
            subprocess.run(
                ["git", "push", remote, branch],
                cwd=git_root,
                check=True,
                capture_output=True,
            )
            print(f"Successfully pushed to {remote}/{branch}")

    except subprocess.CalledProcessError as e:
        raise PublishError(
            f"Git command failed: {e.stderr.decode() if e.stderr else str(e)}"
        ) from e
    finally:
        # Return to original branch/commit
        try:
            if current_ref.startswith("refs/") or len(current_ref) == 40:
                # It's a commit hash (detached HEAD)
                subprocess.run(
                    ["git", "checkout", current_ref],
                    cwd=git_root,
                    check=True,
                    capture_output=True,
                )
            else:
                # It's a branch name
                subprocess.run(
                    ["git", "checkout", current_ref],
                    cwd=git_root,
                    check=True,
                    capture_output=True,
                )
        except subprocess.CalledProcessError:
            print(
                f"Warning: Failed to return to original branch/commit {current_ref}",
                file=sys.stderr,
            )
