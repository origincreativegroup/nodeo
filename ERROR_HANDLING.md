# Error Handling and Feedback System

This document describes the comprehensive error handling and user feedback system implemented in jspow.

## Overview

The error handling system provides:
- **Clear, actionable error messages** with context-specific guidance
- **User feedback widget** for reporting bugs and providing feature requests
- **Automatic error logging** to backend for monitoring
- **Retry mechanisms** with exponential backoff for transient failures
- **Categorized errors** for better debugging and user experience

## Frontend Components

### 1. Error Utilities (`frontend/src/utils/errorHandling.ts`)

#### `createActionableError(error, context)`
Converts raw errors into user-friendly, actionable error objects with:
- **Categorization**: Network, validation, file system, permission, AI model, storage
- **Severity levels**: Info, warning, error, critical
- **Actionable guidance**: Suggested actions the user can take
- **Technical details**: For debugging and bug reports

**Example:**
```typescript
try {
  await renameOperation();
} catch (error) {
  const actionableError = createActionableError(error, {
    operation: 'rename',
    imageCount: 5
  });
  // Shows: "Connection Error: Unable to connect to server. Suggested actions: Retry"
}
```

#### `retryWithBackoff(operation, options)`
Automatically retries failed operations with exponential backoff:
- Default: 3 retries with 1s initial delay, 2x backoff factor
- Configurable max retries and delays
- Optional retry callbacks for progress updates

**Example:**
```typescript
await retryWithBackoff(
  () => applyRename(template, images),
  {
    maxRetries: 2,
    onRetry: (attempt) => {
      toast.loading(`Retrying (attempt ${attempt}/2)...`);
    }
  }
);
```

### 2. User Feedback Components

#### `FloatingFeedbackButton` (`frontend/src/components/FloatingFeedbackButton.tsx`)
- Fixed position button in bottom-right corner
- Always accessible from any page
- Opens feedback modal on click
- ID: `feedback-button` (can be triggered programmatically)

#### `FeedbackWidget` (`frontend/src/components/FeedbackWidget.tsx`)
Full-featured feedback modal supporting:
- **Feedback types**: Bug report, feature request, improvement, other
- **Sentiment tracking**: Positive/negative experience rating
- **Bug reports**: Steps to reproduce, technical details
- **Contact**: Optional email for follow-up
- **System info**: Automatic collection of browser/OS details
- **Pre-filled errors**: Can be called with error details for quick bug reporting

**Features:**
- Form validation
- Loading states
- Success notifications with ticket ID
- System information toggle
- Technical details preview

### 3. Error Display Component

#### `ErrorDisplay` (`frontend/src/components/ErrorDisplay.tsx`)
Displays actionable errors with:
- Color-coded severity (info, warning, error, critical)
- Expandable technical details
- Action buttons (retry, report issue, etc.)
- Dismissible notifications
- Direct link to feedback widget

### 4. Enhanced RenameManager Error Handling

The `RenameManager` component now includes:

#### Improved Error Messages
- **Preview errors**: "No analyzed images to rename. Please upload and analyze images first."
- **Batch errors**: Smart summary (shows all if ≤3 errors, summary if >3)
- **Contextual guidance**: Permission errors → "Check file permissions", Not found → "File may have been moved"

#### Retry Logic
- Automatic retry with backoff for preview, rename, and auto-rename operations
- User feedback during retry attempts
- Toast notifications with progress updates

#### Error State Management
- `currentError` state for displaying actionable errors
- Error dismissal capability
- Error context preservation for bug reports

## Backend Components

### 1. Error Handler (`app/services/error_handler.py`)

#### `DetailedError` class
Structured error representation with:
- Title and user-friendly message
- Category and severity
- Technical details for debugging
- Context dictionary
- Suggestions list
- Timestamp

#### `create_error_response(exception, context)`
Converts Python exceptions to DetailedError objects with:
- Smart categorization (FileNotFoundError → file_system category)
- Context-specific suggestions
- Full traceback preservation

**Example:**
```python
try:
    with open(file_path) as f:
        content = f.read()
except Exception as e:
    error = create_error_response(e, {'filePath': file_path})
    # Returns DetailedError with:
    # - Title: "File Not Found"
    # - Message: "The requested file could not be found: ..."
    # - Suggestions: ["Verify file path", "Check permissions", ...]
```

### 2. API Endpoints

#### `POST /api/feedback`
Accepts user feedback and bug reports.

**Request:**
```json
{
  "type": "bug" | "feature" | "improvement" | "other",
  "title": "Brief summary",
  "description": "Detailed description",
  "stepsToReproduce": "1. Go to...\n2. Click...\n3. See error",
  "email": "user@example.com",
  "sentiment": "positive" | "negative",
  "systemInfo": {
    "userAgent": "...",
    "platform": "...",
    "screenResolution": "..."
  },
  "isErrorReport": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Thank you for your feedback!",
  "ticketId": "A1B2C3D4"
}
```

**What it does:**
- Generates unique ticket ID
- Logs to application logs with `[FEEDBACK-{ticketId}]` prefix
- Returns ticket ID for user reference
- TODO: Store in database, send emails, create GitHub issues

#### `POST /api/errors/log`
Logs frontend errors for monitoring.

**Request:**
```json
{
  "title": "Error title",
  "message": "User-friendly message",
  "category": "network" | "validation" | "file_system" | ...,
  "severity": "info" | "warning" | "error" | "critical",
  "technicalDetails": "Stack trace and details",
  "timestamp": "2025-01-15T10:30:00Z",
  "context": { "operation": "rename", "imageCount": 5 },
  "userAgent": "Mozilla/5.0...",
  "url": "http://localhost:3000/rename"
}
```

**Response:**
```json
{
  "success": true,
  "errorId": "E5F6G7H8"
}
```

**What it does:**
- Generates unique error ID
- Logs with appropriate severity level
- Includes context, user agent, and URL
- Silent failure (doesn't throw errors)
- TODO: Store in database, send to error tracking service (Sentry)

## Usage Examples

### Example 1: Handle Rename Errors

```typescript
const handleRename = async () => {
  setCurrentError(null);

  try {
    const response = await retryWithBackoff(
      () => applyRename(template, images),
      {
        maxRetries: 2,
        onRetry: (attempt) => {
          toast.loading(`Retrying (attempt ${attempt}/2)...`);
        }
      }
    );

    toast.success('Rename successful!');
  } catch (error) {
    const actionableError = createActionableError(error, {
      operation: 'rename',
      template,
      imageCount: images.length
    });

    setCurrentError(actionableError);
    toast.error(actionableError.message);
  }
};
```

### Example 2: Open Feedback Widget Programmatically

```typescript
// From any component
const reportIssue = () => {
  const feedbackButton = document.getElementById('feedback-button');
  if (feedbackButton) {
    feedbackButton.click();
  }
};

// Or with error context
const actionableError = createActionableError(error);
setShowFeedback(true);
setPrefilledError({
  title: actionableError.title,
  message: actionableError.message,
  technicalDetails: actionableError.technicalDetails
});
```

### Example 3: Backend Error Handling

```python
from app.services.error_handler import create_error_response, log_detailed_error

@app.post("/api/some-endpoint")
async def endpoint(data: RequestModel):
    try:
        result = await perform_operation(data)
        return {"success": True, "result": result}
    except Exception as e:
        error = create_error_response(e, {
            "endpoint": "/api/some-endpoint",
            "data": data.dict()
        })
        log_detailed_error(error, logger)
        raise HTTPException(
            status_code=500,
            detail=error.to_dict()
        )
```

## Error Categories

| Category | Description | Example Errors |
|----------|-------------|----------------|
| `network` | Connection issues, timeouts | ERR_NETWORK, ECONNREFUSED, offline |
| `validation` | Invalid input, bad data | 400 status, validation errors |
| `file_system` | File operations | FileNotFoundError, ENOENT |
| `permission` | Access denied | 403 status, PermissionError |
| `ai_model` | AI processing failures | Ollama errors, model not found |
| `storage` | Cloud storage issues | Upload/download failures |
| `database` | Database errors | SQL errors, connection issues |
| `unknown` | Uncategorized errors | Generic exceptions |

## Error Severity Levels

| Severity | Description | User Impact | Actions |
|----------|-------------|-------------|---------|
| `info` | Informational | None | Display message |
| `warning` | Minor issue | Limited | Show warning, continue |
| `error` | Standard error | Moderate | Show error, allow retry |
| `critical` | Severe failure | High | Alert, require action |

## Monitoring and Logging

### Log Format

**Feedback:**
```
[FEEDBACK-A1B2C3D4] Type: BUG | Title: Rename fails | Email: user@example.com
[FEEDBACK-A1B2C3D4] Description: When I try to rename...
[FEEDBACK-A1B2C3D4] Steps to reproduce:
1. Upload images
2. Click rename
3. Error appears
```

**Client Errors:**
```
[CLIENT-ERROR-E5F6G7H8] Connection Error: Unable to connect | Category: network | Severity: error
[CLIENT-ERROR-E5F6G7H8] Technical details: Error: ERR_NETWORK at ...
[CLIENT-ERROR-E5F6G7H8] Context: {'operation': 'rename', 'imageCount': 5}
[CLIENT-ERROR-E5F6G7H8] User Agent: Mozilla/5.0...
```

### Future Enhancements

- **Database storage**: Store errors and feedback in PostgreSQL
- **Error tracking integration**: Send to Sentry, Rollbar, or similar
- **Email notifications**: Alert admins of critical errors
- **GitHub integration**: Auto-create issues from bug reports
- **Error dashboard**: Real-time monitoring UI (`/monitoring` route)
- **Error analytics**: Aggregate stats, trends, common issues
- **User notifications**: Email follow-up on bug reports

## Best Practices

### For Developers

1. **Always use `createActionableError`** for user-facing errors
2. **Provide context** in error creation (operation, data, state)
3. **Use retry logic** for network operations
4. **Log errors to backend** for monitoring
5. **Test error scenarios** to ensure good UX

### For Users

1. **Use the feedback button** to report issues
2. **Include steps to reproduce** for bugs
3. **Provide email** if you want follow-up
4. **Check suggestions** in error messages before reporting

## Files Reference

### Frontend
- `frontend/src/utils/errorHandling.ts` - Error utilities
- `frontend/src/components/FeedbackWidget.tsx` - Feedback modal
- `frontend/src/components/FloatingFeedbackButton.tsx` - Feedback button
- `frontend/src/components/ErrorDisplay.tsx` - Error display component
- `frontend/src/pages/RenameManager.tsx` - Enhanced error handling example
- `frontend/src/App.tsx` - FloatingFeedbackButton integration

### Backend
- `app/services/error_handler.py` - Error handling utilities
- `main.py` - Feedback and error logging endpoints

### Documentation
- `ERROR_HANDLING.md` - This file

## Testing

To test the error handling system:

1. **Network errors**: Disconnect internet, try operations
2. **Validation errors**: Submit empty forms, invalid data
3. **File errors**: Try to rename non-existent files
4. **Feedback widget**: Submit different feedback types
5. **Retry logic**: Simulate transient failures

## Support

For issues with the error handling system itself:
- Check application logs: `logs/app.log`
- Use the feedback widget to report bugs
- Contact: support@jspow.app
