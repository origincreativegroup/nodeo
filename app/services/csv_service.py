"""
CSV Import Service - Handles CSV parsing and asset matching
"""
import csv
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models import (
    CSVImport,
    CSVImportRow,
    CSVImportStatus,
    CSVImportRowStatus,
    Image,
    ActivityLog,
    ActivityActionType,
)


class CSVImportService:
    """Service for handling CSV imports and asset matching"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def parse_csv_file(self, file_path: str) -> Tuple[List[Dict], Optional[str]]:
        """
        Parse CSV file and extract rows

        Returns:
            Tuple of (rows, error_message)
        """
        try:
            rows = []
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                # Try to detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)

                # Use csv.Sniffer to detect dialect
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    reader = csv.DictReader(csvfile, dialect=dialect)
                except csv.Error:
                    # Fallback to default comma delimiter
                    reader = csv.DictReader(csvfile)

                # Validate required columns
                required_columns = {'Asset_Name', 'File_Path'}
                fieldnames = set(reader.fieldnames or [])

                if not required_columns.issubset(fieldnames):
                    missing = required_columns - fieldnames
                    return [], f"Missing required columns: {', '.join(missing)}"

                # Read all rows
                for row in reader:
                    rows.append(row)

            return rows, None
        except Exception as e:
            return [], f"Error parsing CSV: {str(e)}"

    async def create_import_job(
        self,
        filename: str,
        file_path: str,
        total_rows: int,
        metadata: Optional[Dict] = None
    ) -> CSVImport:
        """Create a new CSV import job"""
        csv_import = CSVImport(
            filename=filename,
            file_path=file_path,
            total_rows=total_rows,
            status=CSVImportStatus.PENDING,
            metadata=metadata or {}
        )
        self.db.add(csv_import)
        await self.db.commit()
        await self.db.refresh(csv_import)
        return csv_import

    async def create_import_rows(
        self,
        csv_import_id: UUID,
        rows: List[Dict]
    ) -> List[CSVImportRow]:
        """Create import row records from CSV data"""
        import_rows = []

        for idx, row in enumerate(rows, start=1):
            import_row = CSVImportRow(
                csv_import_id=csv_import_id,
                row_number=idx,
                priority=row.get('Priority'),
                category=row.get('Category'),
                page_component=row.get('Page_Component'),
                asset_name=row.get('Asset_Name'),
                file_path=row.get('File_Path'),
                dimensions=row.get('Dimensions'),
                format=row.get('Format'),
                file_size_target=row.get('File_Size_Target'),
                csv_status=row.get('Status'),
                notes=row.get('Notes'),
                status=CSVImportRowStatus.PENDING
            )
            self.db.add(import_row)
            import_rows.append(import_row)

        await self.db.commit()
        return import_rows

    async def match_asset(self, import_row: CSVImportRow) -> Optional[Image]:
        """
        Find matching asset in database based on CSV row criteria

        Matching strategy:
        1. Exact filename match (highest priority)
        2. Filename contains asset_name
        3. File path match
        4. Fuzzy match on filename
        """
        search_terms = []

        # Build search criteria
        if import_row.asset_name:
            search_terms.append(import_row.asset_name)

        if import_row.file_path:
            # Extract filename from path
            filename = os.path.basename(import_row.file_path)
            if filename:
                search_terms.append(filename)

        if not search_terms:
            return None

        # Try exact match first
        for term in search_terms:
            result = await self.db.execute(
                select(Image).where(
                    or_(
                        Image.current_filename == term,
                        Image.original_filename == term
                    )
                )
            )
            asset = result.scalar_one_or_none()
            if asset:
                return asset

        # Try partial match (contains)
        for term in search_terms:
            # Clean up the search term
            term_clean = term.replace('.jpg', '').replace('.png', '').replace('.jpeg', '')

            result = await self.db.execute(
                select(Image).where(
                    or_(
                        Image.current_filename.ilike(f"%{term_clean}%"),
                        Image.original_filename.ilike(f"%{term_clean}%"),
                        Image.file_path.ilike(f"%{term}%")
                    )
                ).limit(1)
            )
            asset = result.scalar_one_or_none()
            if asset:
                return asset

        return None

    async def calculate_match_score(
        self,
        import_row: CSVImportRow,
        asset: Image
    ) -> float:
        """
        Calculate confidence score for an asset match

        Returns score between 0.0 and 1.0
        """
        score = 0.0

        # Exact filename match = 1.0
        if import_row.asset_name:
            if (asset.current_filename == import_row.asset_name or
                asset.original_filename == import_row.asset_name):
                score = 1.0
                return score

            # Partial filename match = 0.7
            asset_name_clean = import_row.asset_name.replace('.jpg', '').replace('.png', '').replace('.jpeg', '')
            if (asset_name_clean.lower() in asset.current_filename.lower() or
                asset_name_clean.lower() in asset.original_filename.lower()):
                score = 0.7

        # Format match adds 0.1
        if import_row.format:
            asset_ext = os.path.splitext(asset.current_filename)[1].lstrip('.')
            if asset_ext.lower() == import_row.format.lower():
                score += 0.1

        # Dimensions match adds 0.2
        if import_row.dimensions and asset.width and asset.height:
            # Parse dimensions (e.g., "1920x1080")
            if 'x' in import_row.dimensions.lower():
                try:
                    dims = import_row.dimensions.lower().split('x')
                    expected_width = int(dims[0].strip())
                    expected_height = int(dims[1].strip())

                    if asset.width == expected_width and asset.height == expected_height:
                        score += 0.2
                except (ValueError, IndexError):
                    pass

        return min(score, 1.0)

    async def process_import_row(self, import_row: CSVImportRow) -> bool:
        """
        Process a single import row - find matching asset

        Returns True if matched, False otherwise
        """
        try:
            # Find matching asset
            matched_asset = await self.match_asset(import_row)

            if matched_asset:
                # Calculate match score
                match_score = await self.calculate_match_score(import_row, matched_asset)

                # Update import row
                import_row.matched_asset_id = matched_asset.id
                import_row.match_score = match_score
                import_row.status = CSVImportRowStatus.MATCHED
                import_row.processed_at = datetime.utcnow()

                await self.db.commit()
                return True
            else:
                # No match found
                import_row.status = CSVImportRowStatus.NOT_FOUND
                import_row.error_message = "No matching asset found"
                import_row.processed_at = datetime.utcnow()

                await self.db.commit()
                return False

        except Exception as e:
            import_row.status = CSVImportRowStatus.ERROR
            import_row.error_message = str(e)
            import_row.processed_at = datetime.utcnow()

            await self.db.commit()
            return False

    async def process_import_job(self, csv_import_id: UUID) -> CSVImport:
        """
        Process entire CSV import job

        Finds matching assets for all rows
        """
        # Get import job
        result = await self.db.execute(
            select(CSVImport).where(CSVImport.id == csv_import_id)
        )
        csv_import = result.scalar_one_or_none()

        if not csv_import:
            raise ValueError(f"CSV import {csv_import_id} not found")

        # Update status
        csv_import.status = CSVImportStatus.PROCESSING
        csv_import.started_at = datetime.utcnow()
        await self.db.commit()

        try:
            # Get all rows for this import
            result = await self.db.execute(
                select(CSVImportRow)
                .where(CSVImportRow.csv_import_id == csv_import_id)
                .order_by(CSVImportRow.row_number)
            )
            rows = result.scalars().all()

            # Process each row
            matched_count = 0
            failed_count = 0

            for row in rows:
                success = await self.process_import_row(row)
                if success:
                    matched_count += 1
                else:
                    failed_count += 1

                # Update progress
                csv_import.processed_rows += 1
                csv_import.matched_rows = matched_count
                csv_import.failed_rows = failed_count

            # Update final status
            if matched_count == len(rows):
                csv_import.status = CSVImportStatus.COMPLETED
            elif matched_count > 0:
                csv_import.status = CSVImportStatus.PARTIALLY_COMPLETED
            else:
                csv_import.status = CSVImportStatus.FAILED
                csv_import.error_message = "No assets matched"

            csv_import.completed_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(csv_import)

            # Log activity
            activity_log = ActivityLog(
                action_type=ActivityActionType.SCAN,
                status="success",
                metadata={
                    "csv_import_id": str(csv_import_id),
                    "total_rows": csv_import.total_rows,
                    "matched_rows": matched_count,
                    "failed_rows": failed_count
                }
            )
            self.db.add(activity_log)
            await self.db.commit()

            return csv_import

        except Exception as e:
            csv_import.status = CSVImportStatus.FAILED
            csv_import.error_message = str(e)
            csv_import.completed_at = datetime.utcnow()
            await self.db.commit()

            raise

    async def get_import_status(self, csv_import_id: UUID) -> Optional[CSVImport]:
        """Get status of CSV import job"""
        result = await self.db.execute(
            select(CSVImport).where(CSVImport.id == csv_import_id)
        )
        return result.scalar_one_or_none()

    async def get_import_rows(
        self,
        csv_import_id: UUID,
        status_filter: Optional[CSVImportRowStatus] = None
    ) -> List[CSVImportRow]:
        """Get rows for a CSV import, optionally filtered by status"""
        query = select(CSVImportRow).where(CSVImportRow.csv_import_id == csv_import_id)

        if status_filter:
            query = query.where(CSVImportRow.status == status_filter)

        query = query.order_by(CSVImportRow.row_number)

        result = await self.db.execute(query)
        return list(result.scalars().all())
