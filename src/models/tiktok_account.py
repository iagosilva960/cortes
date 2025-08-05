from src.models.user import db
from cryptography.fernet import Fernet
import os
from datetime import datetime

class TikTokAccount(db.Model):
    __tablename__ = 'tiktok_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    encrypted_password = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, inactive, blocked, limited
    last_post_time = db.Column(db.DateTime)
    total_posts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com jobs de postagem
    posting_jobs = db.relationship('PostingJob', backref='tiktok_account', lazy=True)
    
    def __init__(self, username, password):
        self.username = username
        self.encrypted_password = self._encrypt_password(password)
    
    def _get_encryption_key(self):
        """Gera ou recupera a chave de criptografia"""
        key_file = os.path.join(os.path.dirname(__file__), '..', 'database', 'encryption.key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def _encrypt_password(self, password):
        """Criptografa a senha"""
        key = self._get_encryption_key()
        f = Fernet(key)
        return f.encrypt(password.encode()).decode()
    
    def get_decrypted_password(self):
        """Descriptografa e retorna a senha"""
        key = self._get_encryption_key()
        f = Fernet(key)
        return f.decrypt(self.encrypted_password.encode()).decode()
    
    def update_password(self, new_password):
        """Atualiza a senha criptografada"""
        self.encrypted_password = self._encrypt_password(new_password)
        self.updated_at = datetime.utcnow()
    
    def update_status(self, new_status):
        """Atualiza o status da conta"""
        self.status = new_status
        self.updated_at = datetime.utcnow()
    
    def increment_post_count(self):
        """Incrementa o contador de posts"""
        self.total_posts += 1
        self.last_post_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Converte para dicionário (sem senha)"""
        return {
            'id': self.id,
            'username': self.username,
            'status': self.status,
            'last_post_time': self.last_post_time.isoformat() if self.last_post_time else None,
            'total_posts': self.total_posts,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

