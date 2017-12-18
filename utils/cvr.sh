#!/bin/sh
### BEGIN INIT INFO
# Provides: cvr
# Required-Start: alsa-utils
# Required-Stop: alsa-utils
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Run the Conditional Voice Recorder system.
# Description: This file should be used to start and stop the CVR
# system and writes the output to log files.
### END INIT INFO

LOCK_FILE='/var/lock/cvr'
PID_FILE='/var/run/cvr'
DIR='/home/username/cvr/'
COMMAND="python cvr.py Alexa.pmdl"

# This allows us to interrupt kindly before killing the process
interrupt_process() {
    if [ -z "$1" ]; then
        return 2
    fi

    PNAME="$1"
    PID=`ps aux | grep "[0-9] ${PNAME}" | awk '{print $2}'`
    if [ -z "$PID" ]; then
        return 3
    fi

    if [ -z "$2" ]; then
        SIG="INT"
    else
        SIG="$2"
    fi

    kill -s $SIG $PID
    sleep 1

    PID=`ps aux | grep "[0-9] ${PNAME}" | awk '{print $2}'`
    if [ -z "$PID" ]; then
        return 2
    else
        return 1
    fi
}

# Carry out specific functions when asked to by the system
case "$1" in
  start)
    # Only allow CVR once
    if [ -e "${LOCK_FILE}" ]; then
        echo "CVR might be running already. Try running stop first."
        exit 0
    fi
    touch $LOCK_FILE

    cd "$DIR"

    echo -n "Starting CVR... "
    eval "${COMMAND}" >>/var/log/cvr.log 2>&1 &
    echo $! > "${PID_FILE}"
    echo "Done"
    ;;
  stop)
    echo -n "Stopping CVR... "

    interrupt_process "${COMMAND}" "INT"
    result=$?
    if [ $result -eq 3 ]; then
        echo "Not Running"
    elif [ $result -eq 2 ]; then
        echo "Done"
    else
        interrupt_process "${COMMAND}"
        if [ $? -eq 2 ]; then
            echo "Done"
        else
            interrupt_process "${COMMAND}" "INT"
            if [ $? -eq 2 ]; then
                echo "Done"
            else
                interrupt_process "${COMMAND}" "KILL"
            fi
        fi
    fi

    if [ -e "${LOCK_FILE}" ]; then
        rm $LOCK_FILE
    fi
    ;;
  restart)
    /etc/init.d/cvr stop && /etc/init.d/cvr start
    exit 1
    ;;
  *)
    echo "Usage: /etc/init.d/cvr {start|stop|restart}"
    exit 1
    ;;
esac

exit 0
