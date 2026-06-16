#!/bin/bash
# Hook de inicio de sesión — carga contexto de memoria del asistente de inversión

PROJECT_DIR="/home/user/alphadev/investment_assistant"
CONTEXT_DIR="$PROJECT_DIR/process/context"

echo ""
echo "=================================================="
echo " ASISTENTE DE INVERSIÓN PERSONAL v3.0"
echo " Tu segundo cerebro financiero está listo"
echo "=================================================="
echo ""

# Mostrar estado rápido si la base de datos existe
if [ -f "$PROJECT_DIR/memory/investment.db" ]; then
    echo "Memoria cargada: base de datos SQLite activa"

    # Contar posiciones del portfolio
    POSITIONS=$(python3 -c "
import sys, sqlite3
try:
    conn = sqlite3.connect('$PROJECT_DIR/memory/investment.db')
    n = conn.execute('SELECT COUNT(*) FROM portfolio').fetchone()[0]
    conn.close()
    print(f'Portfolio: {n} posiciones')
except:
    print('Portfolio: vacío')
" 2>/dev/null)
    echo "$POSITIONS"

    # Contar señales pendientes
    PENDING=$(python3 -c "
import sys, sqlite3
try:
    conn = sqlite3.connect('$PROJECT_DIR/memory/investment.db')
    n = conn.execute(\"SELECT COUNT(*) FROM signals WHERE status='pending'\").fetchone()[0]
    conn.close()
    print(f'Señales pendientes de evaluación: {n}')
except:
    pass
" 2>/dev/null)
    [ -n "$PENDING" ] && echo "$PENDING"

    # Mostrar última lección aprendida
    LESSON=$(python3 -c "
import sys, sqlite3
try:
    conn = sqlite3.connect('$PROJECT_DIR/memory/investment.db')
    row = conn.execute('SELECT lesson FROM lessons ORDER BY created_at DESC LIMIT 1').fetchone()
    conn.close()
    if row:
        print(f'Última lección: {row[0][:100]}...')
except:
    pass
" 2>/dev/null)
    [ -n "$LESSON" ] && echo "$LESSON"
else
    echo "Primera sesión detectada. Inicializando base de datos..."
    cd "$PROJECT_DIR" && python3 -c "from memory.database import init_db; init_db()" 2>/dev/null
    echo "Base de datos inicializada."
fi

# Cargar contexto de archivos de memoria
if [ -f "$CONTEXT_DIR/all-context.md" ]; then
    echo ""
    echo "Contexto del sistema cargado desde: process/context/all-context.md"
fi

echo ""
echo "Comandos disponibles:"
echo "  python main.py              → Análisis completo del día"
echo "  python main.py --quick      → Análisis rápido"
echo "  python main.py --portfolio  → Ver portfolio"
echo "  python main.py --status     → Estado del sistema"
echo ""
echo "Skills disponibles (dime lo que necesitas en lenguaje natural):"
echo "  'analiza AAPL'  'cuánto arriesgar en NVDA'  'cómo está mi portfolio'"
echo "  'señal rápida de BTC'  'informe del día'  'qué has aprendido'"
echo ""
