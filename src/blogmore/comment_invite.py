"""Comment invitation email resolution for blog posts."""

##############################################################################
# Python imports.
from urllib.parse import quote

##############################################################################
# Application imports.
from blogmore.content_path import resolve_path
from blogmore.parser import Post
from blogmore.post_path import get_post_path_variables


##############################################################################
def get_invite_email_for_post(
    post: "Post", invite_comments: bool, invite_comments_to: str | None
) -> str | None:
    """Compute the comment invitation email address for a post.

    Applies front-matter overrides on top of the global configuration
    values passed in.  The front-matter ``invite_comments`` key, if
    present, overrides *invite_comments*.  The front-matter
    ``invite_comments_to`` key, if present, is used as-is (no template
    expansion) and overrides *invite_comments_to*.

    Args:
        post: The post to compute the invitation email for.
        invite_comments: Global configuration value for ``invite_comments``.
        invite_comments_to: Global configuration template for
            ``invite_comments_to``, or ``None`` if not configured.

    Returns:
        The email address string to use for the comment invitation, or
        ``None`` when no invitation should be shown for this post.
    """
    metadata = post.metadata or {}

    effective_invite = bool(metadata.get("invite_comments", invite_comments))
    if not effective_invite:
        return None

    if "invite_comments_to" in metadata:
        raw = metadata["invite_comments_to"]
        return str(raw) if raw else None

    if invite_comments_to:
        return resolve_path(
            get_post_path_variables(post), invite_comments_to, "invite_comments_to"
        )

    return None


##############################################################################
def build_mailto_url(email: str, subject: str) -> str:
    """Build a ``mailto:`` URL with a URL-encoded subject.

    Args:
        email: The recipient email address.
        subject: The plain-text subject line for the email.

    Returns:
        A ``mailto:`` URL string with the subject query parameter
        percent-encoded (spaces become ``%20``).
    """
    encoded_subject = quote(subject, safe="")
    return f"mailto:{email}?subject={encoded_subject}"


### comment_invite.py ends here
