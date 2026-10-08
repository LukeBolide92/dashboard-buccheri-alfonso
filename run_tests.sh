#!/bin/bash
# Avvia l'app Flask in background, esegue i test, poi la uccide

echo "Avvio app.py su http://localhost:5000"
python app.py &
APP_PID=$!

sleep 3  # Aspetta che l'app sia pronta

echo "Esecuzione test locali..."
python test_lambda.py

# Uccidi il processo dell'app
kill $APP_PID 2>/dev/null

exit 0