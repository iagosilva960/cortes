FROM python:3.11-slim

# Instalar FFmpeg e dependências do sistema
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p src/database src/uploads

# Expor porta
EXPOSE 5000

# Comando para executar a aplicação
CMD ["python", "src/main.py"]

