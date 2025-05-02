#!/bin/bash

# This script is meant to be run after all setup is complete.

# starting backend (backend/app.py)
echo "starting backend..."
cd backend
python app.py > /dev/tty 2>&1 &
BACKEND_PID=$!
cd ..
# starting frontend (in frontend)
echo "starting frontend..."
cd frontend
npm run dev > /dev/tty 2>&1 &
FRONTEND_PID=$!
cd ..
# Wait for all background processes to exit
wait $BACKEND_PID $FRONTEND_PID