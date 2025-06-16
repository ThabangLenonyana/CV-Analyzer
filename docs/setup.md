# CV Analyzer Setup Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- A Google Gemini API key

## Installation Steps

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd CV-Analyzer
```

### 2. Create a Virtual Environment

It's recommended to use a virtual environment to isolate project dependencies.

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your Google Gemini API key:
   ```env
   GEMINI_API_KEY="your-actual-api-key-here"
   GEMINI_MODEL="gemini-2.0-flash"
   ```

   To get a Gemini API key:
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Copy and paste it into your `.env` file

### 5. Test Gemini Connection

Before running the main application, verify your Gemini API connection:

```bash
python test_gemini_connection.py
```

You should see success messages if everything is configured correctly.

### 6. Run the Application

```bash
python -m app.main
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload
```

The application will start on `http://localhost:8000`

## Available Endpoints

- **Main Page**: `http://localhost:8000/`
- **Health Check**: `http://localhost:8000/health`
- **API Documentation**: `http://localhost:8000/docs`
- **API Configuration**: `http://localhost:8000/api/config`

## Configuration Options

The following environment variables can be configured in your `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Google Gemini API key | Required |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.0-flash` |
| `DEBUG` | Enable debug mode | `True` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `MAX_FILE_SIZE_MB` | Maximum upload file size | `10` |
| `ALLOWED_EXTENSIONS` | Comma-separated file extensions | `pdf,docx` |
| `UPLOAD_FOLDER` | Directory for uploaded files | `uploads` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `10` |

## Troubleshooting

### Common Issues

1. **"GEMINI_API_KEY not found" error**
   - Make sure you've created a `.env` file
   - Verify the API key is correctly set in the `.env` file
   - Ensure there are no extra spaces or quotes around the API key

2. **"Module not found" errors**
   - Make sure you've activated your virtual environment
   - Run `pip install -r requirements.txt` again

3. **Connection refused on port 8000**
   - Check if another application is using port 8000
   - Try changing the port in `.env`: `PORT=8001`

4. **File upload issues**
   - Ensure the `uploads` directory exists or will be created
   - Check file size limits in configuration
   - Verify file extensions are allowed (pdf, docx by default)

### Verifying Installation

To verify everything is working:

1. Visit `http://localhost:8000/health` - should show a green "HEALTHY" status
2. Check the API docs at `http://localhost:8000/docs`
3. Test the Gemini connection with the test script

## Development Tips

- Use `DEBUG=True` in development for auto-reload and detailed error messages
- Monitor the console output for helpful logging information
- The application creates necessary directories automatically on startup

## Next Steps

Once the application is running:

1. Build the CV analysis functionality in the `/api/analyze` endpoint
2. Create the frontend interface for uploading CVs and job descriptions
3. Implement the file parsing logic for PDFs and DOCX files
4. Connect the frontend to the backend API

For production deployment, consider:
- Setting `DEBUG=False`
- Using environment-specific `.env` files
- Setting up proper logging
- Implementing rate limiting
- Adding authentication if needed