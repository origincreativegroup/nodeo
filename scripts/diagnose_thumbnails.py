#!/usr/bin/env python3
"""
Diagnostic script to identify and fix images with missing file_path values.
This script helps resolve thumbnail 404 errors by finding images that:
1. Have NULL or empty file_path in the database
2. Have file_path pointing to non-existent files
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, or_
from app.database import get_db_session
from app.models import Image


async def diagnose_images():
    """Diagnose and report on image file_path issues"""

    print("=" * 80)
    print("THUMBNAIL 404 ERROR DIAGNOSTIC")
    print("=" * 80)
    print()

    async for db in get_db_session():
        # Check for NULL/empty file_path
        print("1. Checking for images with NULL or empty file_path...")
        result = await db.execute(
            select(Image.id, Image.original_filename, Image.current_filename, Image.file_path)
            .where(or_(Image.file_path == None, Image.file_path == ''))
        )
        null_path_images = result.all()

        if null_path_images:
            print(f"   ❌ FOUND {len(null_path_images)} images with NULL/empty file_path:")
            for img in null_path_images[:10]:  # Show first 10
                print(f"      - ID: {img.id}, Filename: {img.original_filename or img.current_filename}")
            if len(null_path_images) > 10:
                print(f"      ... and {len(null_path_images) - 10} more")
            print()
            print("   RECOMMENDATION: These images should be deleted and re-uploaded.")
            print(f"   SQL to delete: DELETE FROM images WHERE file_path IS NULL OR file_path = '';")
        else:
            print("   ✓ No images with NULL/empty file_path found.")

        print()

        # Check for file_path pointing to non-existent files
        print("2. Checking for images with file_path pointing to non-existent files...")
        result = await db.execute(
            select(Image.id, Image.original_filename, Image.current_filename, Image.file_path)
            .where(Image.file_path != None)
            .where(Image.file_path != '')
        )
        all_images = result.all()

        missing_files = []
        for img in all_images:
            if not Path(img.file_path).exists():
                missing_files.append(img)

        if missing_files:
            print(f"   ❌ FOUND {len(missing_files)} images with missing files:")
            for img in missing_files[:10]:  # Show first 10
                print(f"      - ID: {img.id}, Filename: {img.original_filename or img.current_filename}")
                print(f"        Path: {img.file_path}")
            if len(missing_files) > 10:
                print(f"      ... and {len(missing_files) - 10} more")
            print()
            print("   RECOMMENDATION: These images should be deleted from the database.")
            print(f"   IDs to delete: {[img.id for img in missing_files[:20]]}")
        else:
            print("   ✓ All images have valid file paths pointing to existing files.")

        print()

        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total images in database: {len(all_images)}")
        print(f"Images with NULL/empty file_path: {len(null_path_images)}")
        print(f"Images with missing files: {len(missing_files)}")
        print(f"Healthy images: {len(all_images) - len(missing_files)}")
        print()

        if null_path_images or missing_files:
            print("ACTION REQUIRED:")
            print("Run the following commands to clean up broken images:")
            print()
            if null_path_images:
                print("# Delete images with NULL file_path:")
                print("docker exec -it jspow-postgres psql -U postgres -d jspow -c \"DELETE FROM images WHERE file_path IS NULL OR file_path = '';\"")
                print()
            if missing_files:
                print("# Delete images with missing files:")
                ids_str = ",".join(str(img.id) for img in missing_files[:50])
                print(f"docker exec -it jspow-postgres psql -U postgres -d jspow -c \"DELETE FROM images WHERE id IN ({ids_str});\"")
        else:
            print("✓ No issues found! All thumbnails should be loading correctly.")

        print()
        print("=" * 80)

        break


if __name__ == "__main__":
    print()
    asyncio.run(diagnose_images())
    print()
