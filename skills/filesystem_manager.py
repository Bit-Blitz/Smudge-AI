import os
from utils.logger import logger

class FilesystemManager:
    def __init__(self):
        pass

    def write_file(self, path, content):
        """Writes content to a file at the specified path.
        If path is just a filename, defaults to User's Downloads folder.
        Resolves relative paths (Desktop/file.txt) automatically.
        Returns the absolute path of the written file on success, or False on failure.
        """
        logger.info(f"Writing to file: {path}")
        try:
            # 1. Expand user home directory (~)
            path = os.path.expanduser(path)
            
            # 2. Handle known relative folder shortcuts if path doesn't start with a drive/root
            # E.g. "Desktop/file.txt" -> "C:/Users/User/Desktop/file.txt"
            if not os.path.isabs(path):
                # Common user folders to check against
                user_home = os.path.expanduser("~")
                first_part = path.split(os.sep)[0].split('/')[0].lower() # Handle both separators
                
                known_folders = {
                    "desktop": os.path.join(user_home, "Desktop"),
                    "documents": os.path.join(user_home, "Documents"),
                    "downloads": os.path.join(user_home, "Downloads"),
                    "music": os.path.join(user_home, "Music"),
                    "pictures": os.path.join(user_home, "Pictures"),
                    "videos": os.path.join(user_home, "Videos")
                }
                
                if first_part in known_folders:
                    # Replace "Desktop" with full path
                    # path = "Desktop/file.txt" -> relative_rest = "file.txt"
                    # We need to be careful with joining
                    parts = path.replace('\\', '/').split('/')
                    if len(parts) > 1:
                        relative_rest = os.path.join(*parts[1:])
                        path = os.path.join(known_folders[first_part], relative_rest)
                    else:
                         # Should not happen if it matched, but safe fallback
                         path = os.path.join(known_folders[first_part])
                
                # 3. Default to Downloads if still no directory structure
                elif not os.path.dirname(path):
                    path = os.path.join(known_folders["downloads"], path)
                    logger.info(f"Path was just a filename. Defaulting to: {path}")
                else:
                    # It's a relative path like "project/data.txt", use CWD or Project Root?
                    # Let's use Project Root or CWD
                    path = os.path.abspath(path)

            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return os.path.abspath(path)
        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            return False

    def read_file(self, path):
        """Reads content from a file."""
        logger.info(f"Reading file: {path}")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            return None

if __name__ == "__main__":
    fm = FilesystemManager()
    fm.write_file("test_file.txt", "Hello World")
