from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.video import PostingJob
from src.models.tiktok_account import TikTokAccount
from datetime import datetime, timedelta
import json

posting_jobs_bp = Blueprint('posting_jobs', __name__)

@posting_jobs_bp.route('/jobs', methods=['GET'])
def get_jobs():
    """Lista todos os jobs de postagem"""
    try:
        status_filter = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = PostingJob.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        jobs = query.order_by(PostingJob.scheduled_time.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Incluir informações da conta e vídeo
        jobs_data = []
        for job in jobs.items:
            job_dict = job.to_dict()
            
            # Adicionar informações da conta
            account = TikTokAccount.query.get(job.tiktok_account_id)
            if account:
                job_dict['account_username'] = account.username
                job_dict['account_status'] = account.status
            
            # Adicionar informações do vídeo
            from src.models.video import Video
            video = Video.query.get(job.video_id)
            if video:
                job_dict['video_filename'] = video.original_filename
                job_dict['video_duration'] = video.get_duration_formatted()
            
            jobs_data.append(job_dict)
        
        return jsonify({
            'success': True,
            'jobs': jobs_data,
            'pagination': {
                'page': jobs.page,
                'pages': jobs.pages,
                'per_page': jobs.per_page,
                'total': jobs.total
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@posting_jobs_bp.route('/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Obtém detalhes de um job específico"""
    try:
        job = PostingJob.query.get_or_404(job_id)
        job_dict = job.to_dict()
        
        # Adicionar informações relacionadas
        account = TikTokAccount.query.get(job.tiktok_account_id)
        if account:
            job_dict['account'] = account.to_dict()
        
        from src.models.video import Video
        video = Video.query.get(job.video_id)
        if video:
            job_dict['video'] = video.to_dict()
        
        return jsonify({
            'success': True,
            'job': job_dict
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@posting_jobs_bp.route('/jobs/<int:job_id>/retry', methods=['POST'])
def retry_job(job_id):
    """Recoloca um job na fila para retry"""
    try:
        job = PostingJob.query.get_or_404(job_id)
        
        if job.status not in ['failed', 'completed']:
            return jsonify({
                'success': False,
                'error': 'Job deve estar com status failed ou completed para retry'
            }), 400
        
        if not job.can_retry():
            return jsonify({
                'success': False,
                'error': 'Número máximo de tentativas excedido'
            }), 400
        
        # Reagendar para 5 minutos a partir de agora
        job.scheduled_time = datetime.utcnow() + timedelta(minutes=5)
        job.status = 'pending'
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        job.increment_retry()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Job reagendado para retry',
            'job': job.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@posting_jobs_bp.route('/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancela um job pendente"""
    try:
        job = PostingJob.query.get_or_404(job_id)
        
        if job.status != 'pending':
            return jsonify({
                'success': False,
                'error': 'Apenas jobs pendentes podem ser cancelados'
            }), 400
        
        job.update_status('failed', 'Cancelado pelo usuário')
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Job cancelado com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@posting_jobs_bp.route('/jobs/stats', methods=['GET'])
def get_jobs_stats():
    """Retorna estatísticas dos jobs"""
    try:
        total_jobs = PostingJob.query.count()
        pending_jobs = PostingJob.query.filter_by(status='pending').count()
        processing_jobs = PostingJob.query.filter_by(status='processing').count()
        completed_jobs = PostingJob.query.filter_by(status='completed').count()
        failed_jobs = PostingJob.query.filter_by(status='failed').count()
        
        # Jobs nas próximas 24 horas
        tomorrow = datetime.utcnow() + timedelta(days=1)
        upcoming_jobs = PostingJob.query.filter(
            PostingJob.scheduled_time <= tomorrow,
            PostingJob.status == 'pending'
        ).count()
        
        # Jobs hoje
        today = datetime.utcnow().date()
        jobs_today = PostingJob.query.filter(
            PostingJob.scheduled_time >= today,
            PostingJob.scheduled_time < today + timedelta(days=1)
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_jobs': total_jobs,
                'pending_jobs': pending_jobs,
                'processing_jobs': processing_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'upcoming_jobs': upcoming_jobs,
                'jobs_today': jobs_today
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@posting_jobs_bp.route('/jobs/process', methods=['POST'])
def process_pending_jobs():
    """Processa jobs pendentes (simulação)"""
    try:
        # Buscar jobs pendentes que devem ser executados agora
        now = datetime.utcnow()
        pending_jobs = PostingJob.query.filter(
            PostingJob.status == 'pending',
            PostingJob.scheduled_time <= now
        ).limit(5).all()  # Processar até 5 jobs por vez
        
        processed_count = 0
        
        for job in pending_jobs:
            # Verificar se a conta está ativa
            account = TikTokAccount.query.get(job.tiktok_account_id)
            if not account or account.status != 'active':
                job.update_status('failed', 'Conta não está ativa')
                continue
            
            # Simular processamento
            job.update_status('processing')
            db.session.commit()
            
            # Aqui seria implementada a lógica real de postagem no TikTok
            # Por enquanto, simula sucesso/falha
            import random
            import time
            
            time.sleep(2)  # Simula tempo de processamento
            
            success = random.choice([True, True, True, False])  # 75% de sucesso
            
            if success:
                job.update_status('completed')
                account.increment_post_count()
                processed_count += 1
            else:
                error_messages = [
                    'Erro de rede durante upload',
                    'Conta temporariamente limitada',
                    'Formato de vídeo não aceito',
                    'Erro interno do TikTok'
                ]
                job.update_status('failed', random.choice(error_messages))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{processed_count} jobs processados com sucesso',
            'processed_count': processed_count,
            'total_pending': len(pending_jobs)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@posting_jobs_bp.route('/jobs/queue', methods=['GET'])
def get_queue_status():
    """Retorna status da fila de postagem"""
    try:
        # Próximos jobs a serem executados
        upcoming_jobs = PostingJob.query.filter_by(status='pending').order_by(
            PostingJob.scheduled_time.asc()
        ).limit(10).all()
        
        queue_data = []
        for job in upcoming_jobs:
            job_dict = job.to_dict()
            
            # Adicionar informações da conta
            account = TikTokAccount.query.get(job.tiktok_account_id)
            if account:
                job_dict['account_username'] = account.username
            
            # Calcular tempo restante
            if job.scheduled_time:
                time_remaining = job.scheduled_time - datetime.utcnow()
                if time_remaining.total_seconds() > 0:
                    job_dict['time_remaining_minutes'] = int(time_remaining.total_seconds() / 60)
                else:
                    job_dict['time_remaining_minutes'] = 0
            
            queue_data.append(job_dict)
        
        return jsonify({
            'success': True,
            'queue': queue_data,
            'queue_length': len(queue_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

