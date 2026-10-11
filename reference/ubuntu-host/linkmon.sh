#!/bin/bash
IF=wlxd037455a3969
while true; do
    T=$(date +%H:%M:%S)
    R1=$(cat /sys/class/net/$IF/statistics/rx_bytes)
    X1=$(cat /sys/class/net/$IF/statistics/tx_bytes)
    G=$(ping -c 3 -W 3 -q 192.168.196.1 2>/dev/null | tail -1 | cut -d= -f2 | cut -d/ -f2)
    N=$(ping -c 3 -W 3 -q 1.1.1.1 2>/dev/null | tail -1 | cut -d= -f2 | cut -d/ -f2)
    R2=$(cat /sys/class/net/$IF/statistics/rx_bytes)
    X2=$(cat /sys/class/net/$IF/statistics/tx_bytes)
    echo "$T GW=${G:-VYPADEK} NET=${N:-VYPADEK} RX=$(( (R2-R1)/1024 ))kB TX=$(( (X2-X1)/1024 ))kB"
    sleep 60
done
