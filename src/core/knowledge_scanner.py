import csv
import logging
import os

logger = logging.getLogger(__name__)


class KnowledgeScanner:
    """
    Scans a local directory for .md, .txt, and .csv files and keeps the history database in sync.
    """

    SUPPORTED_EXTENSIONS = {".md", ".txt", ".csv"}

    def __init__(self, history_mgr):
        self.history_mgr = history_mgr

    def scan_directory(self, target_dir: str) -> int:
        """
        Crawls the target directory and syncs files incrementally.
        Returns the number of added or updated files.
        """
        if not target_dir or not os.path.exists(target_dir):
            logger.warning(f"KnowledgeScanner: Skip scan. Directory does not exist: {target_dir}")
            return 0

        logger.info(f"KnowledgeScanner: Starting incremental scan of {target_dir}")
        indexed_count = 0
        
        # 1. Load current DB state for documents
        all_records = self.history_mgr.get_all_meetings()
        db_docs = {
            r["file_path"]: {"id": r["id"], "mtime": r.get("file_mtime")} 
            for r in all_records if r.get("source_type") == "document"
        }

        # Sets to track what we've seen on disk vs what's in DB
        found_on_disk = set()

        # 2. Iterate disk files
        for root, _, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                abs_path = os.path.abspath(file_path)
                ext = os.path.splitext(file)[1].lower()

                if ext in self.SUPPORTED_EXTENSIONS:
                    found_on_disk.add(abs_path)
                    try:
                        mtime = os.path.getmtime(abs_path)
                        db_info = db_docs.get(abs_path)

                        # Decision: Index if new or file modified
                        if not db_info:
                            self._process_file(abs_path, ext, mtime)
                            indexed_count += 1
                        elif db_info["mtime"] is None or mtime > db_info["mtime"]:
                            logger.info(f"KnowledgeScanner: Update detected for {abs_path}")
                            # Delete old record and re-insert to refresh search index
                            self.history_mgr.delete_meeting(db_info["id"])
                            self._process_file(abs_path, ext, mtime)
                            indexed_count += 1
                        else:
                            # Already in DB and mtime matches
                            continue
                            
                    except Exception as e:
                        logger.error(f"Failed to process file {abs_path}: {e}")

        # 3. Handle Deletions (files in DB but gone from disk)
        for path, info in db_docs.items():
            if path not in found_on_disk:
                logger.info(f"KnowledgeScanner: Removing deleted file from DB: {path}")
                try:
                    self.history_mgr.delete_meeting(info["id"])
                except Exception as e:
                    logger.warning(f"Failed to delete ghost record {path}: {e}")

        logger.info(f"KnowledgeScanner: Scan complete. {indexed_count} files processed.")
        return indexed_count

    def _process_file(self, file_path: str, ext: str, mtime: float):
        """Parses a single file and adds it to the history manager."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                raw_content = f.read()

            if ext == ".csv":
                import io
                reader = csv.reader(io.StringIO(raw_content))
                content = "\n".join([", ".join(row) for row in reader])
                title = os.path.basename(file_path)
                project_name = "Knowledge Library"
                category = "CSV"
            else:
                # MD/TXT: Handle YAML Frontmatter
                header_data = {}
                content = raw_content
                if raw_content.startswith("---"):
                    parts = raw_content.split("---", 2)
                    if len(parts) >= 3:
                        header_str = parts[1]
                        content = parts[2].strip()
                        # Simple YAML-ish parser
                        for line in header_str.splitlines():
                            if ":" in line:
                                k, v = line.split(":", 1)
                                header_data[k.strip().lower()] = v.strip().strip("\"'")

                title = header_data.get("title") or os.path.basename(file_path)
                project_name = header_data.get("project") or "Knowledge Library"
                category = header_data.get("category") or ext.upper()[1:]

            self.history_mgr.add_meeting(
                title=title,
                transcript=content,
                audio_path="",
                project_name=project_name,
                category=category,
                source_type="document",
                file_path=file_path,
                file_mtime=mtime
            )
            logger.info(f"KnowledgeScanner: Indexed {title} (Project: {project_name})")

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
