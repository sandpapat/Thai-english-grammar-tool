#!/bin/bash

# Production startup script for Thai-English Grammar Learning Tool
# Use this for quick deployment without systemd

set -e

echo "🚀 Starting Thai-English App in Production Mode"

# Check if gunicorn config exists
if [ ! -f "gunicorn_config.py" ]; then
    echo "❌ gunicorn_config.py not found in current directory"
    exit 1
fi

# Set production environment variables
export FLASK_ENV=production
export SECRET_KEY="${SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_hex(32))')}"

echo "📝 Environment:"
echo "  - FLASK_ENV: $FLASK_ENV"
echo "  - SECRET_KEY: Set (hidden)"
echo "  - TOGETHER_API_KEY: $(if [ -n "$TOGETHER_API_KEY" ]; then echo "Set"; else echo "Not set (will use mock explanations)"; fi)"

# Check if models directory exists
if [ ! -d "models" ] && [ ! -f "models/typhoon-translate-4b-q4_k_m.gguf" ]; then
    echo "⚠️  Warning: models directory not found. Application will use mock implementations."
fi

# Kill any existing gunicorn processes
echo "🔍 Checking for existing processes..."
if pgrep -f "gunicorn.*thai-english-app" > /dev/null; then
    echo "🛑 Stopping existing gunicorn processes..."
    pkill -f "gunicorn.*thai-english-app" || true
    sleep 3
fi

# Start with different methods based on preference
echo "🎯 Choose startup method:"
echo "1) Screen session (recommended for development/testing)"
echo "2) Nohup background process"
echo "3) Foreground (Ctrl+C to stop)"

read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo "🖥️  Starting in screen session 'thai-app'..."
        screen -dmS thai-app gunicorn -c gunicorn_config.py app:app
        sleep 3
        
        if screen -list | grep -q thai-app; then
            echo "✅ Started successfully in screen session!"
            echo "   - Attach: screen -r thai-app"
            echo "   - Detach: Ctrl+A then D"
            echo "   - Kill: screen -X -S thai-app quit"
        else
            echo "❌ Failed to start in screen"
            exit 1
        fi
        ;;
    
    2)
        echo "🔧 Starting with nohup..."
        nohup gunicorn -c gunicorn_config.py app:app > app.log 2>&1 &
        PID=$!
        echo $PID > app.pid
        sleep 3
        
        if ps -p $PID > /dev/null; then
            echo "✅ Started successfully with PID $PID"
            echo "   - Logs: tail -f app.log"
            echo "   - Stop: kill $PID (or kill \$(cat app.pid))"
            echo "   - PID saved to app.pid"
        else
            echo "❌ Failed to start with nohup"
            exit 1
        fi
        ;;
    
    3)
        echo "🔧 Starting in foreground..."
        echo "   Press Ctrl+C to stop"
        gunicorn -c gunicorn_config.py app:app
        ;;
    
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

if [ "$choice" != "3" ]; then
    echo ""
    echo "🌐 Application URLs:"
    echo "  - Main app: http://localhost:5000"
    echo "  - Health check: http://localhost:5000/health"
    echo "  - Rate limit info: http://localhost:5000/api/rate-limit-info"
    echo ""
    echo "🔧 Monitoring:"
    echo "  - Check process: pgrep -f gunicorn"
    echo "  - View connections: netstat -tlnp | grep 5000"
    echo "  - Test health: curl http://localhost:5000/health | jq"
    echo ""
    
    # Quick health check
    echo "🏥 Testing health check (waiting 10s for models to load)..."
    sleep 10
    
    if curl -s http://localhost:5000/health > /dev/null 2>&1; then
        echo "✅ Health check passed!"
        curl -s http://localhost:5000/health | python3 -m json.tool 2>/dev/null || echo "Health endpoint responding"
    else
        echo "⚠️  Health check not responding yet (models may still be loading)"
    fi
fi

echo "🎉 Startup complete!"