# CSV Import Feature Documentation

## Overview

The CSV Import feature allows you to bulk upload a list of required assets and automatically match them against existing images in your jspow database. This is useful for:

- **Asset Auditing**: Verify which required assets exist in your library
- **Batch Matching**: Find multiple assets at once based on naming criteria
- **Project Planning**: Track which assets are available vs. needed for a project
- **Inventory Management**: Match a list of required files against your collection

## CSV File Format

### Required Columns

The CSV file **must** include these columns:
- `Asset_Name` - The name of the asset file (e.g., "hero-banner.jpg")
- `File_Path` - The expected file path (e.g., "/assets/images/hero-banner.jpg")

### Optional Columns

Additional columns that provide context:
- `Priority` - Priority level (1-5, or High/Medium/Low)
- `Category` - Asset category (e.g., "Hero", "Product", "Icon")
- `Page_Component` - Where the asset will be used (e.g., "Homepage Banner")
- `Dimensions` - Expected dimensions (e.g., "1920x1080")
- `Format` - File format (e.g., "jpg", "png", "svg")
- `File_Size_Target` - Target file size (e.g., "500KB")
- `Status` - Current status (e.g., "Needed", "In Progress", "Complete")
- `Notes` - Additional notes or comments

### Example CSV

```csv
Priority,Category,Page_Component,Asset_Name,File_Path,Dimensions,Format,File_Size_Target,Status,Notes
1,Hero,Homepage Banner,hero-banner-main.jpg,/assets/images/hero-banner-main.jpg,1920x1080,jpg,500KB,Needed,Main homepage hero image
2,Product,Product Grid,product-001.png,/assets/products/product-001.png,800x600,png,200KB,Needed,Product catalog image
```

A complete sample CSV is available at: `examples/sample_asset_upload.csv`

## API Endpoints

### 1. Upload CSV and Start Import

**Endpoint**: `POST /api/v2/csv/import`

**Description**: Upload a CSV file and start the asset matching process.

**Request**:
```bash
curl -X POST "http://localhost:8002/api/v2/csv/import" \
  -F "file=@/path/to/your/assets.csv"
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "assets.csv",
  "status": "processing",
  "total_rows": 10,
  "processed_rows": 0,
  "matched_rows": 0,
  "failed_rows": 0,
  "error_message": null,
  "created_at": "2025-11-15T10:30:00Z",
  "started_at": "2025-11-15T10:30:01Z",
  "completed_at": null
}
```

### 2. List All Imports

**Endpoint**: `GET /api/v2/csv`

**Description**: Get a list of all CSV import jobs.

**Query Parameters**:
- `status_filter` (optional) - Filter by status: `pending`, `processing`, `completed`, `failed`, `partially_completed`
- `limit` (optional, default: 50) - Number of results to return
- `offset` (optional, default: 0) - Offset for pagination

**Request**:
```bash
curl "http://localhost:8002/api/v2/csv?status_filter=completed&limit=10"
```

**Response**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "assets.csv",
    "status": "completed",
    "total_rows": 10,
    "processed_rows": 10,
    "matched_rows": 8,
    "failed_rows": 2,
    "created_at": "2025-11-15T10:30:00Z",
    "completed_at": "2025-11-15T10:30:15Z"
  }
]
```

### 3. Get Import Details

**Endpoint**: `GET /api/v2/csv/{import_id}`

**Description**: Get detailed information about a specific import, including all rows and matching results.

**Query Parameters**:
- `include_assets` (optional, default: false) - Include matched asset details

**Request**:
```bash
curl "http://localhost:8002/api/v2/csv/550e8400-e29b-41d4-a716-446655440000?include_assets=true"
```

**Response**:
```json
{
  "import_info": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "assets.csv",
    "status": "completed",
    "total_rows": 10,
    "matched_rows": 8,
    "failed_rows": 2
  },
  "rows": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "row_number": 1,
      "status": "matched",
      "asset_name": "hero-banner-main.jpg",
      "file_path": "/assets/images/hero-banner-main.jpg",
      "matched_asset_id": 123,
      "match_score": 1.0,
      "priority": "1",
      "category": "Hero",
      "dimensions": "1920x1080",
      "format": "jpg"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440002",
      "row_number": 2,
      "status": "not_found",
      "asset_name": "missing-image.jpg",
      "error_message": "No matching asset found"
    }
  ],
  "matched_assets": [
    {
      "id": 123,
      "filename": "hero-banner-main.jpg",
      "file_path": "/storage/images/hero-banner-main.jpg",
      "width": 1920,
      "height": 1080
    }
  ]
}
```

### 4. Get Import Rows

**Endpoint**: `GET /api/v2/csv/{import_id}/rows`

**Description**: Get just the rows for a specific import.

**Query Parameters**:
- `status_filter` (optional) - Filter by row status: `pending`, `matched`, `not_found`, `error`

**Request**:
```bash
curl "http://localhost:8002/api/v2/csv/550e8400-e29b-41d4-a716-446655440000/rows?status_filter=not_found"
```

### 5. Get Import Statistics

**Endpoint**: `GET /api/v2/csv/stats`

**Description**: Get aggregate statistics across all imports.

**Request**:
```bash
curl "http://localhost:8002/api/v2/csv/stats"
```

**Response**:
```json
{
  "total_imports": 25,
  "pending_imports": 2,
  "processing_imports": 1,
  "completed_imports": 20,
  "failed_imports": 2
}
```

### 6. Delete Import

**Endpoint**: `DELETE /api/v2/csv/{import_id}`

**Description**: Delete a CSV import job and all its rows.

**Request**:
```bash
curl -X DELETE "http://localhost:8002/api/v2/csv/550e8400-e29b-41d4-a716-446655440000"
```

## Asset Matching Algorithm

The CSV import service uses a multi-stage matching algorithm to find assets:

### 1. Exact Match (Score: 1.0)
- Compares `Asset_Name` with `current_filename` or `original_filename`
- If exact match found, returns immediately with perfect score

### 2. Partial Match (Base Score: 0.7)
- Strips file extensions (.jpg, .png, .jpeg)
- Searches for asset name within filename (case-insensitive)
- Also searches file paths

### 3. Score Bonuses

Additional factors that increase match confidence:

- **Format Match** (+0.1): File extension matches expected format
- **Dimension Match** (+0.2): Width and height match expected dimensions exactly

### Example Match Scores

```
Asset_Name: "hero-banner.jpg"
Database: "hero-banner.jpg" → Score: 1.0 (exact match)

Asset_Name: "hero-banner.jpg"
Database: "new-hero-banner.jpg" → Score: 0.7 (partial match)

Asset_Name: "logo.png", Format: "png", Dimensions: "400x100"
Database: "logo.png" (400x100, png) → Score: 1.0 (exact + format + dimensions)
```

## WebSocket Updates

The CSV import feature broadcasts real-time updates via WebSocket:

### Connect to WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8002/ws/progress');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'csv_import_started') {
    console.log('Import started:', message.import_id);
  }

  if (message.type === 'csv_import_completed') {
    console.log('Import completed:', message.matched_rows, 'matched');
  }
};
```

### Event Types

- `csv_import_started` - Import job has started
- `csv_import_completed` - Import job has finished

## Usage Workflow

### Step 1: Prepare Your CSV

1. Create a CSV file with your required assets
2. Include at minimum: `Asset_Name` and `File_Path`
3. Add optional columns for better tracking and matching

### Step 2: Upload CSV

```bash
curl -X POST "http://localhost:8002/api/v2/csv/import" \
  -F "file=@my-assets.csv"
```

Save the returned `import_id`.

### Step 3: Monitor Progress

```bash
# Check overall status
curl "http://localhost:8002/api/v2/csv/{import_id}"

# Or connect via WebSocket for real-time updates
```

### Step 4: Review Results

```bash
# Get detailed results with asset info
curl "http://localhost:8002/api/v2/csv/{import_id}?include_assets=true"

# Get only unmatched rows
curl "http://localhost:8002/api/v2/csv/{import_id}/rows?status_filter=not_found"
```

### Step 5: Take Action

Based on the results:
- **Matched assets** - Verify the matches are correct
- **Not found assets** - Upload missing files or adjust search criteria
- **Errors** - Review error messages and fix data issues

## Database Schema

### csv_imports Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| filename | String(500) | Original CSV filename |
| file_path | String(1000) | Stored file path |
| status | Enum | Import status |
| total_rows | Integer | Total CSV rows |
| processed_rows | Integer | Rows processed |
| matched_rows | Integer | Successfully matched |
| failed_rows | Integer | Failed to match |
| error_message | Text | Error details if failed |
| metadata | JSON | Additional import info |
| created_at | DateTime | Creation timestamp |
| started_at | DateTime | Processing start time |
| completed_at | DateTime | Completion time |

### csv_import_rows Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| csv_import_id | UUID | Foreign key to import |
| row_number | Integer | Row number in CSV |
| status | Enum | Row processing status |
| priority | String(50) | Priority from CSV |
| category | String(255) | Category from CSV |
| page_component | String(255) | Component from CSV |
| asset_name | String(500) | Asset name from CSV |
| file_path | String(1000) | File path from CSV |
| dimensions | String(100) | Dimensions from CSV |
| format | String(50) | Format from CSV |
| file_size_target | String(100) | Size target from CSV |
| csv_status | String(100) | Status from CSV |
| notes | Text | Notes from CSV |
| matched_asset_id | Integer | Matched asset ID |
| match_score | Float | Match confidence (0-1) |
| error_message | Text | Error if failed |
| created_at | DateTime | Creation timestamp |
| processed_at | DateTime | Processing time |

## Error Handling

### Common Errors

**Invalid CSV Format**
```json
{
  "detail": "Missing required columns: Asset_Name, File_Path"
}
```

**File Upload Error**
```json
{
  "detail": "File must be a CSV file"
}
```

**Import Not Found**
```json
{
  "detail": "CSV import {id} not found"
}
```

## Best Practices

1. **Consistent Naming**: Use consistent file naming in your CSV that matches your actual filenames
2. **Include Dimensions**: Adding dimensions improves match accuracy
3. **Use Format Field**: Specify file format for better matching
4. **Review Low Scores**: Check matches with scores < 0.8 for accuracy
5. **Clean Data**: Remove duplicate rows before uploading
6. **Batch Size**: Keep CSVs under 1000 rows for optimal performance

## Migration

To apply the database migration:

```bash
# Inside Docker container
docker exec -it jspow-app alembic upgrade head

# Or during app startup (automatic)
```

## Future Enhancements

Potential future improvements:
- Fuzzy string matching for better asset name matching
- AI-powered visual matching using image embeddings
- Export unmatched assets to CSV
- Bulk asset tagging from CSV data
- Integration with project management tools
