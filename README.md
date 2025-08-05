# TikTok Automation Platform

Uma plataforma web completa para automação de postagens no TikTok com processamento automático de vídeos e gerenciamento de múltiplas contas.

## ⚠️ Aviso Importante

**Este projeto é apenas para fins educacionais e de demonstração.** O uso de automação em massa no TikTok pode violar os termos de serviço da plataforma e resultar no banimento das contas. A API oficial do TikTok limita postagens automatizadas a 5 usuários por 24 horas para aplicações não auditadas.

## 🚀 Funcionalidades

### 📱 Gerenciamento de Contas
- Adicionar múltiplas contas do TikTok
- Armazenamento seguro de credenciais com criptografia AES-256
- Teste de conectividade das contas
- Monitoramento de status (ativa/inativa/bloqueada/limitada)

### 🎬 Processamento de Vídeos
- Upload de vídeos até 100MB
- Corte automático em diferentes formatos:
  - **Vertical (9:16)** - TikTok padrão
  - **Quadrado (1:1)** - Para feeds
  - **Horizontal cortado** - Conversão de 16:9 para 9:16
- Preview dos cortes antes da postagem
- Suporte para MP4, MOV, AVI, MKV, WebM

### 🤖 Automação de Postagem
- Postagem escalonada em múltiplas contas
- Intervalo configurável entre postagens
- Sistema de fila com retry automático
- Logs detalhados de cada tentativa
- Monitoramento em tempo real

### 📊 Dashboard e Monitoramento
- Estatísticas em tempo real
- Visualização da fila de postagem
- Histórico de vídeos processados
- Taxa de sucesso das postagens

## 🛠️ Tecnologias Utilizadas

### Backend
- **Flask** - Framework web Python
- **SQLAlchemy** - ORM para banco de dados
- **SQLite** - Banco de dados
- **FFmpeg** - Processamento de vídeo
- **Cryptography** - Criptografia de credenciais
- **Flask-CORS** - Suporte a CORS

### Frontend
- **React** - Framework JavaScript
- **Tailwind CSS** - Estilização
- **shadcn/ui** - Componentes UI
- **Lucide Icons** - Ícones
- **React Router** - Roteamento

## 📦 Instalação e Configuração

### Pré-requisitos
- Python 3.11+
- Node.js 20+
- FFmpeg
- Git

### 1. Clone o repositório
```bash
git clone https://github.com/iagosilva960/cortes.git
cd cortes
```

### 2. Configure o backend
```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\\Scripts\\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configure o frontend (desenvolvimento)
```bash
# Se você quiser modificar o frontend
cd ../tiktok-frontend
npm install
npm run build

# Copiar build para Flask
cp -r dist/* ../cortes/src/static/
```

### 4. Execute a aplicação
```bash
cd cortes
source venv/bin/activate
python src/main.py
```

A aplicação estará disponível em `http://localhost:5000`

## 🚀 Deploy no Fly.io

### 1. Instale o Fly CLI
```bash
curl -L https://fly.io/install.sh | sh
```

### 2. Faça login no Fly.io
```bash
fly auth login
```

### 3. Crie um arquivo `fly.toml`
```toml
app = "tiktok-automation"
primary_region = "gru"

[build]

[http_service]
  internal_port = 5000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512

[env]
  PORT = "5000"
```

### 4. Crie um `Dockerfile`
```dockerfile
FROM python:3.11-slim

# Instalar FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "src/main.py"]
```

### 5. Deploy
```bash
fly deploy
```

## 📁 Estrutura do Projeto

```
cortes/
├── src/
│   ├── models/           # Modelos do banco de dados
│   │   ├── user.py
│   │   ├── tiktok_account.py
│   │   └── video.py
│   ├── routes/           # Rotas da API
│   │   ├── user.py
│   │   ├── tiktok_accounts.py
│   │   ├── videos.py
│   │   └── posting_jobs.py
│   ├── static/           # Frontend React (build)
│   ├── database/         # Banco de dados SQLite
│   └── main.py          # Arquivo principal
├── requirements.txt      # Dependências Python
├── .gitignore
└── README.md
```

## 🔒 Segurança

- **Criptografia**: Todas as credenciais são criptografadas com AES-256
- **Chave de criptografia**: Gerada automaticamente e armazenada localmente
- **CORS**: Configurado para permitir acesso do frontend
- **Validação**: Validação de entrada em todas as rotas da API

## ⚖️ Limitações e Considerações Legais

1. **API do TikTok**: Limitada a 5 usuários/24h para apps não auditados
2. **Termos de Serviço**: Automação pode violar os termos do TikTok
3. **Rate Limiting**: Implementado para evitar detecção de spam
4. **Responsabilidade**: Use por sua própria conta e risco

## 🤝 Contribuição

Este projeto é para fins educacionais. Contribuições são bem-vindas para melhorar a segurança, performance e funcionalidades.

## 📄 Licença

Este projeto é fornecido "como está" para fins educacionais. Use com responsabilidade e de acordo com os termos de serviço das plataformas envolvidas.

## 🆘 Suporte

Para questões técnicas, abra uma issue no GitHub. Lembre-se de que este projeto não oferece suporte para contornar limitações ou termos de serviço de plataformas.

---

**Desenvolvido com ❤️ para fins educacionais**

