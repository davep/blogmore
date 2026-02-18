"""Tests for the publisher module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from blogmore.publisher import (
    PublishError,
    check_git_available,
    check_is_git_repository,
    get_git_root,
    publish_site,
)


class TestCheckGitAvailable:
    """Tests for check_git_available function."""

    def test_git_available(self) -> None:
        """Test when git is available in PATH."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            assert check_git_available() is True

    def test_git_not_available(self) -> None:
        """Test when git is not available in PATH."""
        with patch("shutil.which", return_value=None):
            assert check_git_available() is False


class TestCheckIsGitRepository:
    """Tests for check_is_git_repository function."""

    def test_is_git_repository(self) -> None:
        """Test when path is in a git repository."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert check_is_git_repository(Path("/some/path")) is True
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--git-dir"],
                cwd=Path("/some/path"),
                capture_output=True,
                check=False,
            )

    def test_not_git_repository(self) -> None:
        """Test when path is not in a git repository."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert check_is_git_repository(Path("/some/path")) is False

    def test_subprocess_exception(self) -> None:
        """Test when subprocess raises an exception."""
        with patch("subprocess.run", side_effect=Exception("Test error")):
            assert check_is_git_repository(Path("/some/path")) is False

    def test_default_path_uses_cwd(self) -> None:
        """Test that default path is current working directory."""
        with patch("subprocess.run") as mock_run, patch(
            "pathlib.Path.cwd", return_value=Path("/current/dir")
        ):
            mock_run.return_value = MagicMock(returncode=0)
            check_is_git_repository()
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--git-dir"],
                cwd=Path("/current/dir"),
                capture_output=True,
                check=False,
            )


class TestGetGitRoot:
    """Tests for get_git_root function."""

    def test_get_git_root_success(self) -> None:
        """Test successfully getting git root."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="/path/to/repo\n"
            )
            result = get_git_root(Path("/some/path"))
            assert result == Path("/path/to/repo")
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=Path("/some/path"),
                capture_output=True,
                check=True,
                text=True,
            )

    def test_get_git_root_not_in_repo(self) -> None:
        """Test error when not in a git repository."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            with pytest.raises(PublishError, match="Not in a git repository"):
                get_git_root(Path("/some/path"))

    def test_default_path_uses_cwd(self) -> None:
        """Test that default path is current working directory."""
        with patch("subprocess.run") as mock_run, patch(
            "pathlib.Path.cwd", return_value=Path("/current/dir")
        ):
            mock_run.return_value = MagicMock(
                returncode=0, stdout="/path/to/repo\n"
            )
            get_git_root()
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=Path("/current/dir"),
                capture_output=True,
                check=True,
                text=True,
            )


class TestPublishSite:
    """Tests for publish_site function."""

    def test_publish_site_git_not_available(self, tmp_path: Path) -> None:
        """Test error when git is not available."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>")

        with patch("blogmore.publisher.check_git_available", return_value=False):
            with pytest.raises(PublishError, match="Git command not found"):
                publish_site(output_dir)

    def test_publish_site_not_in_git_repo(self, tmp_path: Path) -> None:
        """Test error when not in a git repository."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>")

        with patch(
            "blogmore.publisher.check_git_available", return_value=True
        ), patch(
            "blogmore.publisher.check_is_git_repository", return_value=False
        ):
            with pytest.raises(
                PublishError, match="Not in a git repository"
            ):
                publish_site(output_dir)

    def test_publish_site_output_dir_not_exists(self, tmp_path: Path) -> None:
        """Test error when output directory doesn't exist."""
        output_dir = tmp_path / "output"

        with patch(
            "blogmore.publisher.check_git_available", return_value=True
        ), patch(
            "blogmore.publisher.check_is_git_repository", return_value=True
        ), patch(
            "blogmore.publisher.get_git_root", return_value=tmp_path
        ):
            with pytest.raises(
                PublishError, match="Output directory not found"
            ):
                publish_site(output_dir)

    def test_publish_site_output_dir_empty(self, tmp_path: Path) -> None:
        """Test error when output directory is empty."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch(
            "blogmore.publisher.check_git_available", return_value=True
        ), patch(
            "blogmore.publisher.check_is_git_repository", return_value=True
        ), patch(
            "blogmore.publisher.get_git_root", return_value=tmp_path
        ):
            with pytest.raises(
                PublishError, match="Output directory is empty"
            ):
                publish_site(output_dir)

    @patch("blogmore.publisher.subprocess.run")
    @patch("blogmore.publisher.shutil.rmtree")
    @patch("blogmore.publisher.shutil.copy2")
    @patch("blogmore.publisher.shutil.copytree")
    @patch("blogmore.publisher.tempfile.mkdtemp")
    @patch("blogmore.publisher.check_git_available", return_value=True)
    @patch("blogmore.publisher.check_is_git_repository", return_value=True)
    @patch("blogmore.publisher.get_git_root")
    def test_publish_site_new_branch(
        self,
        mock_get_git_root: MagicMock,
        mock_check_is_git_repository: MagicMock,
        mock_check_git_available: MagicMock,
        mock_mkdtemp: MagicMock,
        mock_copytree: MagicMock,
        mock_copy2: MagicMock,
        mock_rmtree: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test publishing site to a new branch."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>")

        git_root = tmp_path / "repo"
        git_root.mkdir()
        mock_get_git_root.return_value = git_root

        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        mock_mkdtemp.return_value = str(worktree_path)

        # Mock git commands
        def run_side_effect(*args: object, **kwargs: object) -> MagicMock:
            cmd = args[0] if args else []
            if not isinstance(cmd, list):
                return MagicMock(returncode=0, stdout="")

            if cmd[:3] == ["git", "rev-parse", "--verify"]:
                # Branch doesn't exist locally
                return MagicMock(returncode=1, stdout="")
            elif cmd[:2] == ["git", "ls-remote"]:
                # Branch doesn't exist remotely
                return MagicMock(returncode=0, stdout="")
            elif cmd[:2] == ["git", "diff"]:
                # There are changes
                return MagicMock(returncode=1, stdout="")
            else:
                return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = run_side_effect

        publish_site(output_dir, branch="gh-pages", remote="origin")

        # Verify git worktree commands were called
        assert any(
            call[0][0][:2] == ["git", "worktree"]
            for call in mock_run.call_args_list
        )
        assert any(
            call[0][0][:3] == ["git", "checkout", "--orphan"]
            for call in mock_run.call_args_list
        )
        assert any(
            call[0][0][:2] == ["git", "add"]
            for call in mock_run.call_args_list
        )
        assert any(
            call[0][0][:2] == ["git", "commit"]
            for call in mock_run.call_args_list
        )
        assert any(
            call[0][0][:2] == ["git", "push"]
            for call in mock_run.call_args_list
        )

    @patch("blogmore.publisher.subprocess.run")
    @patch("blogmore.publisher.shutil.rmtree")
    @patch("blogmore.publisher.shutil.copy2")
    @patch("blogmore.publisher.shutil.copytree")
    @patch("blogmore.publisher.tempfile.mkdtemp")
    @patch("blogmore.publisher.check_git_available", return_value=True)
    @patch("blogmore.publisher.check_is_git_repository", return_value=True)
    @patch("blogmore.publisher.get_git_root")
    def test_publish_site_existing_branch(
        self,
        mock_get_git_root: MagicMock,
        mock_check_is_git_repository: MagicMock,
        mock_check_git_available: MagicMock,
        mock_mkdtemp: MagicMock,
        mock_copytree: MagicMock,
        mock_copy2: MagicMock,
        mock_rmtree: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test publishing site to an existing branch."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>")

        git_root = tmp_path / "repo"
        git_root.mkdir()
        mock_get_git_root.return_value = git_root

        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        mock_mkdtemp.return_value = str(worktree_path)

        # Mock git commands
        def run_side_effect(*args: object, **kwargs: object) -> MagicMock:
            cmd = args[0] if args else []
            if not isinstance(cmd, list):
                return MagicMock(returncode=0, stdout="")

            if cmd[:3] == ["git", "rev-parse", "--verify"]:
                # Branch exists locally
                return MagicMock(returncode=0, stdout="")
            elif cmd[:2] == ["git", "diff"]:
                # There are changes
                return MagicMock(returncode=1, stdout="")
            else:
                return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = run_side_effect

        publish_site(output_dir, branch="gh-pages", remote="origin")

        # Verify git worktree commands were called
        assert any(
            call[0][0][:3] == ["git", "worktree", "add"]
            for call in mock_run.call_args_list
        )
        assert any(
            call[0][0][:2] == ["git", "add"]
            for call in mock_run.call_args_list
        )
        assert any(
            call[0][0][:2] == ["git", "add"]
            for call in mock_run.call_args_list
        )

    @patch("blogmore.publisher.subprocess.run")
    @patch("blogmore.publisher.shutil.rmtree")
    @patch("blogmore.publisher.shutil.copy2")
    @patch("blogmore.publisher.shutil.copytree")
    @patch("blogmore.publisher.tempfile.mkdtemp")
    @patch("blogmore.publisher.check_git_available", return_value=True)
    @patch("blogmore.publisher.check_is_git_repository", return_value=True)
    @patch("blogmore.publisher.get_git_root")
    def test_publish_site_no_changes(
        self,
        mock_get_git_root: MagicMock,
        mock_check_is_git_repository: MagicMock,
        mock_check_git_available: MagicMock,
        mock_mkdtemp: MagicMock,
        mock_copytree: MagicMock,
        mock_copy2: MagicMock,
        mock_rmtree: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test publishing site when there are no changes."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>")

        git_root = tmp_path / "repo"
        git_root.mkdir()
        mock_get_git_root.return_value = git_root

        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        mock_mkdtemp.return_value = str(worktree_path)

        # Mock git commands
        def run_side_effect(*args: object, **kwargs: object) -> MagicMock:
            cmd = args[0] if args else []
            if not isinstance(cmd, list):
                return MagicMock(returncode=0, stdout="")

            if cmd[:3] == ["git", "rev-parse", "--verify"]:
                # Branch exists
                return MagicMock(returncode=0, stdout="")
            elif cmd[:2] == ["git", "diff"]:
                # No changes
                return MagicMock(returncode=0, stdout="")
            else:
                return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = run_side_effect

        publish_site(output_dir, branch="gh-pages", remote="origin")

        captured = capsys.readouterr()
        assert "No changes to publish" in captured.out
        # Should not push if there are no changes
        assert not any(
            call[0][0][:2] == ["git", "push"]
            for call in mock_run.call_args_list
        )
