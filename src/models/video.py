from src.models.user import db
from datetime import datetime
import os

class Video(db.Model):
    __tablename__ = 'videos'
    
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # em bytes
    duration = db.Column(db.Float)  # em segundos
    resolution = db.Column(db.String(20))  # ex: "1920x1080"
    format = db.Column(db.String(10))  # ex: "mp4", "mov"
    
    # Configurações de processamento
    cut_vertical = db.Column(db.Boolean, default=True)
    cut_square = db.Column(db.Boolean, default=True)
    cut_horizontal = db.Column(db.Boolean, default=False)
    
    # Metadados
    caption = db.Column(db.Text)
    hashtags = db.Column(db.Text)
    
    # Status do processamento
    processing_status = db.Column(db.String(20), default='uploaded')  # uploaded, processing, processed, error
    processed_files = db.Column(db.Text)  # JSON com caminhos dos arquivos processados
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com jobs de postagem
    posting_jobs = db.relationship('PostingJob', backref='video', lazy=True)
    
    def get_file_size_mb(self):
        """Retorna o tamanho do arquivo em MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    def get_duration_formatted(self):
        """Retorna a duração formatada em MM:SS"""
        if self.duration:
            minutes = int(self.duration // 60)
            seconds = int(self.duration % 60)
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"
    
    def update_processing_status(self, status, processed_files=None):
        """Atualiza o status do processamento"""
        self.processing_status = status
        if processed_files:
            self.processed_files = processed_files
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'file_size_mb': self.get_file_size_mb(),
            'duration': self.get_duration_formatted(),
            'resolution': self.resolution,
            'format': self.format,
            'cut_vertical': self.cut_vertical,
            'cut_square': self.cut_square,
            'cut_horizontal': self.cut_horizontal,
            'caption': self.caption,
            'hashtags': self.hashtags,
            'processing_status': self.processing_status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class PostingJob(db.Model):
    __tablename__ = 'posting_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    tiktok_account_id = db.Column(db.Integer, db.ForeignKey('tiktok_accounts.id'), nullable=False)
    
    # Configurações da postagem
    video_variant = db.Column(db.String(20), nullable=False)  # vertical, square, horizontal
    video_file_path = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.Text)
    
    # Status e timing
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed, retrying
    scheduled_time = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Controle de retry
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    # Logs e erros
    error_message = db.Column(db.Text)
    log_data = db.Column(db.Text)  # JSON com logs detalhados
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def update_status(self, status, error_message=None):
        """Atualiza o status do job"""
        self.status = status
        if error_message:
            self.error_message = error_message
        
        if status == 'processing':
            self.started_at = datetime.utcnow()
        elif status in ['completed', 'failed']:
            self.completed_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
    
    def increment_retry(self):
        """Incrementa o contador de retry"""
        self.retry_count += 1
        self.updated_at = datetime.utcnow()
    
    def can_retry(self):
        """Verifica se pode tentar novamente"""
        return self.retry_count < self.max_retries
    
    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'video_id': self.video_id,
            'tiktok_account_id': self.tiktok_account_id,
            'video_variant': self.video_variant,
            'caption': self.caption,
            'status': self.status,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

