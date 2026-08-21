'''
Shared helper utilities used across multiple modules
'''


def timecode_to_sectors(timestamp: str) -> int:
    """Convert a MM:SS:FF CD timecode string to a total sector count."""
    parts = timestamp.split(':')
    if len(parts) != 3:
        return 0
    minutes, seconds, frames = map(int, parts)
    return minutes * 60 * 75 + seconds * 75 + frames