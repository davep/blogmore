"""Git publishing functionality for blogmore."""

import datetime as dt
import shutil
import subprocess
import tempfile
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
    3. Uses a temporary git worktree to prepare the branch
    4. If the branch exists locally, fetches from remote to ensure it is
       up-to-date (handles multi-machine publishing scenarios)
    5. Copies only the output directory contents to the worktree
    6. Ensures a .nojekyll file exists in the root (for GitHub Pages)
    7. Commits the changes
    8. Pushes to the remote
    9. Cleans up the worktree

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

    # Make output_dir absolute for copying
    output_dir = output_dir.resolve()

    print(f"Publishing site to branch '{branch}' on remote '{remote}'...")

    # Create a temporary directory for the worktree
    temp_dir = tempfile.mkdtemp(prefix="blogmore-publish-")
    worktree_path = Path(temp_dir)

    try:
        # Check if the branch exists (locally or remotely)
        branch_check_result = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            cwd=git_root,
            capture_output=True,
            check=False,
        )
        branch_exists_locally = branch_check_result.returncode == 0

        if not branch_exists_locally:
            # Check if it exists on remote
            remote_branch_check = subprocess.run(
                ["git", "ls-remote", "--heads", remote, branch],
                cwd=git_root,
                capture_output=True,
                check=False,
                text=True,
            )
            branch_exists_remotely = bool(remote_branch_check.stdout.strip())

            if branch_exists_remotely:
                # Fetch the remote branch
                subprocess.run(
                    ["git", "fetch", remote, f"{branch}:{branch}"],
                    cwd=git_root,
                    check=True,
                    capture_output=True,
                )
                print(f"Fetched existing branch '{branch}' from remote")
                branch_exists_locally = True
        else:
            # Branch exists locally - fetch from remote to ensure it is
            # up-to-date. This handles the multi-machine publishing scenario
            # where another machine has already published newer content; without
            # this step the subsequent push would be rejected as non-fast-forward.
            fetch_result = subprocess.run(
                ["git", "fetch", remote, f"+{branch}:{branch}"],
                cwd=git_root,
                capture_output=True,
                check=False,
            )
            if fetch_result.returncode == 0:
                print(f"Fetched latest '{branch}' from remote")

        if branch_exists_locally:
            # Create worktree from existing branch
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), branch],
                cwd=git_root,
                check=True,
                capture_output=True,
            )
            print(f"Created worktree for existing branch '{branch}'")

            # Remove all files from worktree (but keep .git)
            for item in worktree_path.iterdir():
                if item.name != ".git":
                    if item.is_file() or item.is_symlink():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
        else:
            # Create worktree with new orphan branch
            subprocess.run(
                ["git", "worktree", "add", "--detach", str(worktree_path)],
                cwd=git_root,
                check=True,
                capture_output=True,
            )
            # Create orphan branch in the worktree
            subprocess.run(
                ["git", "checkout", "--orphan", branch],
                cwd=worktree_path,
                check=True,
                capture_output=True,
            )
            # Remove all files
            subprocess.run(
                ["git", "rm", "-rf", "."],
                cwd=worktree_path,
                check=False,
                capture_output=True,
            )
            print(f"Created worktree with new orphan branch '{branch}'")

        # Copy all files from output directory to worktree
        for item in output_dir.iterdir():
            dest = worktree_path / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)

        # Ensure .nojekyll file exists in the root
        nojekyll_file = worktree_path / ".nojekyll"
        if not nojekyll_file.exists():
            nojekyll_file.touch()
            print("Created .nojekyll file")

        # Add all files in the worktree
        subprocess.run(
            ["git", "add", "-A"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Check if there are any changes to commit
        diff_result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=worktree_path,
            check=False,
        )

        if diff_result.returncode == 0:
            print("No changes to publish")
        else:
            # Commit the changes with UTC timestamp
            timestamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            commit_message = f"Publish site - {timestamp}"
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=worktree_path,
                check=True,
                capture_output=True,
            )
            print("Changes committed")

            # Push to remote
            subprocess.run(
                ["git", "push", remote, branch],
                cwd=worktree_path,
                check=True,
                capture_output=True,
            )
            print(f"Successfully pushed to {remote}/{branch}")

    except subprocess.CalledProcessError as e:
        raise PublishError(
            f"Git command failed: {e.stderr.decode() if e.stderr else str(e)}"
        ) from e
    finally:
        # Clean up the worktree
        try:
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=git_root,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            # If worktree remove fails, try manual cleanup
            try:
                shutil.rmtree(worktree_path, ignore_errors=True)
            except Exception:
                pass
