#!/bin/bash

# Script simple para actualizar el repositorio de GitHub
# Uso: ./update.sh "Tu mensaje de commit"

MENSAJE=$1

if [ -z "$MENSAJE" ]; then
    MENSAJE="Actualización: $(date +'%Y-%m-%d %H:%M:%S')"
fi

echo "🚀 Agregando cambios..."
git add .

echo "📝 Realizando commit: $MENSAJE"
git commit -m "$MENSAJE"

echo "☁️ Subiendo a GitHub..."
git push origin main

echo "✅ ¡Listo! Proyecto actualizado."
