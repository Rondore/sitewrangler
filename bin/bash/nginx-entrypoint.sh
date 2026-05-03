#!/bin/bash

# Function to handle SIGTERM signal
term_handler() {
    echo "Received SIGTERM signal. Shutting down Nginx..."
    nginx -s stop
    exit 0
}

# Trap the SIGTERM signal
trap 'term_handler' SIGTERM