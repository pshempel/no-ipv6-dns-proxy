import grp
import logging
import os
import pwd
import sys

logger = logging.getLogger(__name__)


def drop_privileges(user: str, group: str):
    """Drop root privileges to specified user/group"""
    if os.getuid() != 0:
        logger.info("Not running as root, skipping privilege drop")
        return

    try:
        # Get user and group info
        user_info = pwd.getpwnam(user)
        group_info = grp.getgrnam(group)

        # Set group first
        os.setgid(group_info.gr_gid)
        os.setgroups([])

        # Set user
        os.setuid(user_info.pw_uid)

        logger.info(f"Dropped privileges to {user}:{group}")

    except KeyError as e:
        logger.error(f"User or group not found: {e}")
        sys.exit(1)
    except OSError as e:
        logger.error(f"Failed to drop privileges: {e}")
        sys.exit(1)


def create_pid_file(pid_file: str):
    """Create PID file with directory validation"""
    try:
        # Ensure directory exists
        pid_dir = os.path.dirname(pid_file)
        if pid_dir and not os.path.exists(pid_dir):
            # Modified by Claude: 2025-01-11 - Added directory creation with validation
            try:
                os.makedirs(pid_dir, mode=0o755)
                logger.info(f"Created PID directory: {pid_dir}")
            except OSError as e:
                logger.error(f"Failed to create PID directory {pid_dir}: {e}")
                raise

        # Create the PID file
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        logger.info(f"PID file created: {pid_file}")
    except Exception as e:
        logger.error(f"Failed to create PID file {pid_file}: {e}")


def remove_pid_file(pid_file: str):
    """Remove PID file"""
    try:
        if os.path.exists(pid_file):
            os.unlink(pid_file)
            logger.info(f"PID file removed: {pid_file}")
    except Exception as e:
        logger.error(f"Failed to remove PID file {pid_file}: {e}")
