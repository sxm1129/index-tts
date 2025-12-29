#!/bin/bash

# IndexTTS API Server Management Script
# Usage: ./api_server.sh {start|stop|status|restart}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_ENV="xsmartvoice_env"
PYTHON_BIN="/data1/miniconda3/envs/${CONDA_ENV}/bin/python"
API_SERVER="${SCRIPT_DIR}/api_server.py"
API_PORT=8050
LOG_FILE="/tmp/api_server.log"
PID_FILE="/tmp/api_server.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored message
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if process is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            # Check if it's actually our api_server process
            if ps -p "$PID" -o cmd= | grep -q "api_server.py"; then
                return 0
            fi
        fi
    fi
    
    # Also check by process name
    if pgrep -f "api_server.py.*--api_port.*8050" > /dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Get PID of running process
get_pid() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "$PID"
            return 0
        fi
    fi
    
    # Try to find by process name
    PID=$(pgrep -f "api_server.py.*--api_port.*8050" | head -1)
    if [ -n "$PID" ]; then
        echo "$PID"
        return 0
    fi
    
    return 1
}

# Check if port is in use
check_port() {
    if netstat -tlnp 2>/dev/null | grep -q ":${API_PORT} " || ss -tlnp 2>/dev/null | grep -q ":${API_PORT} "; then
        return 0
    fi
    return 1
}

# Start the API server
start() {
    print_info "Starting IndexTTS API Server..."
    
    # Check if already running
    if is_running; then
        PID=$(get_pid)
        print_warn "API Server is already running (PID: $PID)"
        print_info "Use './api_server.sh stop' to stop it first"
        return 1
    fi
    
    # Check if port is in use
    if check_port; then
        print_error "Port ${API_PORT} is already in use"
        netstat -tlnp 2>/dev/null | grep ":${API_PORT} " || ss -tlnp 2>/dev/null | grep ":${API_PORT} "
        return 1
    fi
    
    # Check if conda environment exists
    if [ ! -f "$PYTHON_BIN" ]; then
        print_error "Python binary not found: $PYTHON_BIN"
        print_error "Please check conda environment: $CONDA_ENV"
        return 1
    fi
    
    # Check if api_server.py exists
    if [ ! -f "$API_SERVER" ]; then
        print_error "API server script not found: $API_SERVER"
        return 1
    fi
    
    # Set environment variables
    export HF_ENDPOINT="https://hf-mirror.com"
    
    # Start the server
    cd "$SCRIPT_DIR"
    print_info "Working directory: $SCRIPT_DIR"
    print_info "Log file: $LOG_FILE"
    print_info "Port: $API_PORT"
    
    nohup "$PYTHON_BIN" "$API_SERVER" --fp16 --api_port ${API_PORT} > "$LOG_FILE" 2>&1 &
    
    # Save PID
    NEW_PID=$!
    echo "$NEW_PID" > "$PID_FILE"
    
    # Wait a moment and check if process started
    sleep 3
    
    if is_running; then
        print_info "✓ API Server started successfully (PID: $NEW_PID)"
        print_info "Waiting for model to load..."
        
        # Wait for port to be listening (max 120 seconds)
        for i in {1..24}; do
            if check_port; then
                print_info "✓ Port ${API_PORT} is now listening"
                
                # Test health endpoint
                if command -v curl > /dev/null 2>&1; then
                    sleep 2
                    HEALTH_STATUS=$(curl -s http://localhost:${API_PORT}/api/v1/health 2>/dev/null | grep -o '"status":"healthy"')
                    if [ -n "$HEALTH_STATUS" ]; then
                        print_info "✓ Health check passed"
                        print_info "API Server is ready to accept requests"
                        print_info "API URL: http://localhost:${API_PORT}"
                        return 0
                    fi
                fi
                return 0
            fi
            echo -n "."
            sleep 5
        done
        
        print_warn "Server started but port not listening yet"
        print_info "Check logs: tail -f $LOG_FILE"
        return 0
    else
        print_error "✗ Failed to start API Server"
        print_error "Check logs: tail $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Stop the API server
stop() {
    print_info "Stopping IndexTTS API Server..."
    
    if ! is_running; then
        print_warn "API Server is not running"
        rm -f "$PID_FILE"
        return 0
    fi
    
    PID=$(get_pid)
    
    if [ -z "$PID" ]; then
        print_error "Cannot determine PID"
        return 1
    fi
    
    print_info "Stopping process (PID: $PID)..."
    
    # Try graceful shutdown first
    kill "$PID" 2>/dev/null
    
    # Wait for process to stop (max 10 seconds)
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            print_info "✓ Process stopped gracefully"
            rm -f "$PID_FILE"
            
            # Wait for GPU memory to be released
            print_info "Waiting for GPU memory release..."
            sleep 3
            
            # Verify GPU memory released
            if command -v nvidia-smi > /dev/null 2>&1; then
                if nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -q "^${PID}$"; then
                    print_warn "GPU memory not yet released, waiting..."
                    sleep 2
                else
                    print_info "✓ GPU memory released"
                fi
            fi
            
            return 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    print_warn "Process did not stop gracefully, forcing..."
    kill -9 "$PID" 2>/dev/null
    sleep 2
    
    if ! ps -p "$PID" > /dev/null 2>&1; then
        print_info "✓ Process force stopped"
        rm -f "$PID_FILE"
        
        # Wait for GPU memory release
        print_info "Waiting for GPU memory release..."
        sleep 3
        print_info "✓ GPU memory should be released now"
        return 0
    else
        print_error "✗ Failed to stop process"
        return 1
    fi
}

# Show server status
status() {
    echo "==============================================="
    echo "IndexTTS API Server Status"
    echo "==============================================="
    
    if is_running; then
        PID=$(get_pid)
        echo -e "Status:      ${GREEN}RUNNING${NC}"
        echo "PID:         $PID"
        echo "Port:        $API_PORT"
        
        # Get process info
        if ps -p "$PID" > /dev/null 2>&1; then
            PROCESS_INFO=$(ps -p "$PID" -o pid,pcpu,pmem,vsz,rss,etime,cmd --no-headers)
            CPU=$(echo "$PROCESS_INFO" | awk '{print $2}')
            MEM=$(echo "$PROCESS_INFO" | awk '{print $3}')
            ETIME=$(echo "$PROCESS_INFO" | awk '{print $6}')
            
            echo "CPU:         ${CPU}%"
            echo "Memory:      ${MEM}%"
            echo "Uptime:      $ETIME"
        fi
        
        # Check port
        if check_port; then
            echo -e "Port Status: ${GREEN}LISTENING${NC}"
            
            # Try health check
            if command -v curl > /dev/null 2>&1; then
                HEALTH=$(curl -s http://localhost:${API_PORT}/api/v1/health 2>/dev/null)
                if [ -n "$HEALTH" ]; then
                    MODEL_VER=$(echo "$HEALTH" | grep -o '"model_version":"[^"]*"' | cut -d'"' -f4)
                    DEVICE=$(echo "$HEALTH" | grep -o '"device":"[^"]*"' | cut -d'"' -f4)
                    FP16=$(echo "$HEALTH" | grep -o '"fp16_enabled":[^,}]*' | cut -d':' -f2)
                    PROMPTS=$(echo "$HEALTH" | grep -o '"available_prompts":[0-9]*' | cut -d':' -f2)
                    
                    echo "Model:       v${MODEL_VER}"
                    echo "Device:      ${DEVICE}"
                    echo "FP16:        ${FP16}"
                    echo "Prompts:     ${PROMPTS}"
                fi
            fi
        else
            echo -e "Port Status: ${YELLOW}NOT LISTENING YET${NC}"
            echo "(Model may still be loading...)"
        fi
        
        # GPU memory info
        if command -v nvidia-smi > /dev/null 2>&1; then
            GPU_MEM=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits 2>/dev/null | grep "^${PID}," | awk -F',' '{print $2}')
            if [ -n "$GPU_MEM" ]; then
                echo "GPU Memory:  ${GPU_MEM} MB"
            fi
        fi
        
        echo "Log file:    $LOG_FILE"
        echo "API URL:     http://localhost:${API_PORT}"
        
    else
        echo -e "Status:      ${RED}STOPPED${NC}"
        echo "Port:        $API_PORT"
        
        # Check if port is still in use
        if check_port; then
            echo -e "Port Status: ${YELLOW}IN USE BY ANOTHER PROCESS${NC}"
            netstat -tlnp 2>/dev/null | grep ":${API_PORT} " || ss -tlnp 2>/dev/null | grep ":${API_PORT} "
        else
            echo "Port Status: FREE"
        fi
    fi
    
    echo "==============================================="
}

# Restart the server
restart() {
    print_info "Restarting IndexTTS API Server..."
    
    # Stop if running
    if is_running; then
        print_info "Stopping existing server..."
        stop
        
        # Extra wait to ensure GPU memory is released
        print_info "Waiting for GPU memory to be fully released..."
        sleep 5
        
        # Verify no api_server processes are running
        if pgrep -f "api_server.py" > /dev/null 2>&1; then
            print_warn "Found lingering processes, cleaning up..."
            pkill -9 -f "api_server.py"
            sleep 3
        fi
        
        # Verify GPU memory released
        if command -v nvidia-smi > /dev/null 2>&1; then
            print_info "Checking GPU memory..."
            nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>/dev/null | grep "api_server"
        fi
    fi
    
    # Start server
    print_info "Starting server..."
    start
}

# Main script
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    restart)
        restart
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the API server"
        echo "  stop    - Stop the API server (releases GPU memory)"
        echo "  status  - Show server status"
        echo "  restart - Restart the API server (releases GPU before restart)"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 status"
        echo "  $0 restart"
        exit 1
        ;;
esac

exit $?

