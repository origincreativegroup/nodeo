"""
File renaming engine with preview and batch operations
"""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging
from app.services.template_parser import TemplateParser

logger = logging.getLogger(__name__)


class RenameEngine:
    """Engine for file renaming operations"""

    def __init__(self, template: str = "{description}_{date}_{index}"):
        """
        Initialize rename engine

        Args:
            template: Naming template to use
        """
        self.template = template
        self.parser = TemplateParser(template)

    def generate_filename(
        self,
        metadata: Dict,
        index: int = 1,
        original_extension: str = None
    ) -> str:
        """
        Generate new filename from metadata

        Args:
            metadata: Image metadata dict
            index: Index for batch operations
            original_extension: File extension to preserve

        Returns:
            New filename with extension
        """
        base_name = self.parser.apply(metadata, index=index)

        if original_extension:
            ext = original_extension.lstrip('.')
            return f"{base_name}.{ext}"
        return base_name

    def preview_batch(
        self,
        images_metadata: List[Dict],
        start_index: int = 1
    ) -> List[Dict]:
        """
        Generate preview of batch rename operation

        Args:
            images_metadata: List of image metadata dicts
            start_index: Starting index for sequential numbering

        Returns:
            List of preview dicts with:
                - original_filename
                - proposed_filename
                - metadata
        """
        previews = []

        for idx, metadata in enumerate(images_metadata, start=start_index):
            original = metadata.get('original_filename', 'unknown.jpg')
            ext = Path(original).suffix

            new_filename = self.generate_filename(
                metadata,
                index=idx,
                original_extension=ext
            )

            previews.append({
                'original_filename': original,
                'proposed_filename': new_filename,
                'metadata': metadata,
                'index': idx
            })

        return previews

    def apply_rename(
        self,
        file_path: str,
        new_filename: str,
        create_backup: bool = True
    ) -> Dict:
        """
        Apply rename to a single file

        Args:
            file_path: Current file path
            new_filename: New filename (with extension)
            create_backup: Create backup before renaming

        Returns:
            {
                'success': bool,
                'old_path': str,
                'new_path': str,
                'backup_path': str (if created),
                'error': str (if failed)
            }
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f"File not found: {file_path}"
                }

            # Determine new path
            new_path = file_path.parent / new_filename

            # Check if target already exists
            if new_path.exists() and new_path != file_path:
                return {
                    'success': False,
                    'error': f"Target file already exists: {new_filename}"
                }

            result = {
                'success': True,
                'old_path': str(file_path),
                'new_path': str(new_path)
            }

            # Create backup if requested
            if create_backup:
                backup_path = file_path.parent / f".backup_{file_path.name}"
                shutil.copy2(file_path, backup_path)
                result['backup_path'] = str(backup_path)
                logger.info(f"Created backup: {backup_path}")

            # Perform rename
            file_path.rename(new_path)
            logger.info(f"Renamed: {file_path} -> {new_path}")

            return result

        except Exception as e:
            logger.error(f"Error renaming {file_path}: {e}")
            return {
                'success': False,
                'old_path': str(file_path),
                'error': str(e)
            }

    def apply_batch_rename(
        self,
        rename_specs: List[Dict],
        create_backups: bool = True,
        stop_on_error: bool = False
    ) -> Dict:
        """
        Apply batch rename operation

        Args:
            rename_specs: List of dicts with:
                - file_path: Current path
                - new_filename: Target filename
            create_backups: Create backups before renaming
            stop_on_error: Stop processing on first error

        Returns:
            {
                'total': int,
                'succeeded': int,
                'failed': int,
                'results': List[Dict],
                'errors': List[Dict]
            }
        """
        results = []
        errors = []

        for spec in rename_specs:
            result = self.apply_rename(
                spec['file_path'],
                spec['new_filename'],
                create_backup=create_backups
            )

            results.append(result)

            if not result['success']:
                errors.append(result)
                if stop_on_error:
                    logger.warning("Stopping batch rename due to error")
                    break

        summary = {
            'total': len(rename_specs),
            'succeeded': sum(1 for r in results if r['success']),
            'failed': len(errors),
            'results': results,
            'errors': errors
        }

        logger.info(
            f"Batch rename completed: {summary['succeeded']}/{summary['total']} succeeded"
        )

        return summary

    def rollback(self, results: List[Dict]) -> Dict:
        """
        Rollback rename operations using backup files

        Args:
            results: Results from apply_batch_rename

        Returns:
            Summary of rollback operation
        """
        rollback_results = []
        rollback_errors = []

        for result in results:
            if not result.get('success'):
                continue

            backup_path = result.get('backup_path')
            if not backup_path or not Path(backup_path).exists():
                rollback_errors.append({
                    'file': result.get('new_path'),
                    'error': 'No backup found'
                })
                continue

            try:
                new_path = Path(result['new_path'])
                backup = Path(backup_path)

                # Restore from backup
                if new_path.exists():
                    new_path.unlink()

                shutil.move(backup, result['old_path'])

                rollback_results.append({
                    'success': True,
                    'restored': result['old_path']
                })

                logger.info(f"Rolled back: {result['new_path']} -> {result['old_path']}")

            except Exception as e:
                logger.error(f"Rollback error for {result.get('new_path')}: {e}")
                rollback_errors.append({
                    'file': result.get('new_path'),
                    'error': str(e)
                })

        return {
            'total': len(results),
            'succeeded': len(rollback_results),
            'failed': len(rollback_errors),
            'results': rollback_results,
            'errors': rollback_errors
        }

    def cleanup_backups(self, directory: str):
        """
        Remove backup files from directory

        Args:
            directory: Directory to clean
        """
        dir_path = Path(directory)
        backup_files = list(dir_path.glob('.backup_*'))

        for backup in backup_files:
            try:
                backup.unlink()
                logger.info(f"Removed backup: {backup}")
            except Exception as e:
                logger.error(f"Error removing backup {backup}: {e}")

        logger.info(f"Cleaned up {len(backup_files)} backup files")
