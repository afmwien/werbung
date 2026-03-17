#!/bin/bash
# Ads Manager - Server Management Script
# Für Froxlor/Shared Hosting ohne sudo

APP_DIR="/var/customers/webs/afmadmin/werbung"
VENV_DIR="$APP_DIR/.venv"
PID_FILE="$APP_DIR/.uvicorn.pid"
LOG_DIR="$APP_DIR/logs"
PORT=8001

cd "$APP_DIR"
source "$VENV_DIR/bin/activate"

# Log-Verzeichnis erstellen
mkdir -p "$LOG_DIR"

case "$1" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "Server läuft bereits (PID: $(cat $PID_FILE))"
            exit 1
        fi

        echo "Starte Ads Manager auf Port $PORT..."
        nohup uvicorn main:app --host 127.0.0.1 --port $PORT > "$LOG_DIR/uvicorn.log" 2>&1 &
        echo $! > "$PID_FILE"
        echo "Gestartet (PID: $(cat $PID_FILE))"
        ;;

    stop)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 $PID 2>/dev/null; then
                echo "Stoppe Server (PID: $PID)..."
                kill $PID
                rm "$PID_FILE"
                echo "Gestoppt"
            else
                echo "Prozess nicht gefunden, entferne PID-Datei"
                rm "$PID_FILE"
            fi
        else
            echo "Server läuft nicht (keine PID-Datei)"
        fi
        ;;

    restart)
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "Server läuft (PID: $(cat $PID_FILE))"
            echo "Port: $PORT"
            echo "Logs: $LOG_DIR/uvicorn.log"
        else
            echo "Server läuft nicht"
        fi
        ;;

    logs)
        tail -f "$LOG_DIR/uvicorn.log"
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
