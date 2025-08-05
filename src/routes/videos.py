from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from src.models.user import db
from src.models.video import Video, PostingJob
from src.models.tiktok_account import TikTokAccount
import os
import json
from datetime import datetime, timedelta
import ffmpeg

videos_bp = Blueprint('videos', __name__)

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_video_info(file_path):
    """Extrai informações do vídeo usando ffmpeg"""
    try:
        probe = ffmpeg.probe(file_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        
        if video_stream:
            duration = float(probe['format']['duration'])
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            
            return {
                'duration': duration,
                'resolution': f"{width}x{height}",
                'width': width,
                'height': height
            }
    except Exception as e:
        print(f"Erro ao extrair informações do vídeo: {e}")
    
    return None

def process_video_cuts(video_id):
    """Processa os cortes do vídeo em diferentes formatos"""
    try:
        video = Video.query.get(video_id)
        if not video:
            return False
        
        video.update_processing_status('processing')
        db.session.commit()
        
        input_path = video.file_path
        base_name = os.path.splitext(video.original_filename)[0]
        output_dir = os.path.join(os.path.dirname(input_path), 'processed')
        os.makedirs(output_dir, exist_ok=True)
        
        processed_files = {}
        
        # Obter informações do vídeo original
        video_info = get_video_info(input_path)
        if not video_info:
            video.update_processing_status('error')
            db.session.commit()
            return False
        
        original_width = video_info['width']
        original_height = video_info['height']
        
        # Corte vertical (9:16) - TikTok padrão
        if video.cut_vertical:
            output_path = os.path.join(output_dir, f"{base_name}_vertical.mp4")
            
            # Calcular dimensões para 9:16
            target_height = original_height
            target_width = int(target_height * 9 / 16)
            
            if target_width <= original_width:
                # Crop horizontal
                x_offset = (original_width - target_width) // 2
                (
                    ffmpeg
                    .input(input_path)
                    .filter('crop', target_width, target_height, x_offset, 0)
                    .output(output_path, vcodec='libx264', acodec='aac')
                    .overwrite_output()
                    .run(quiet=True)
                )
            else:
                # Scale down
                (
                    ffmpeg
                    .input(input_path)
                    .filter('scale', target_width, target_height)
                    .output(output_path, vcodec='libx264', acodec='aac')
                    .overwrite_output()
                    .run(quiet=True)
                )
            
            processed_files['vertical'] = output_path
        
        # Corte quadrado (1:1)
        if video.cut_square:
            output_path = os.path.join(output_dir, f"{base_name}_square.mp4")
            
            # Usar a menor dimensão como base
            size = min(original_width, original_height)
            x_offset = (original_width - size) // 2
            y_offset = (original_height - size) // 2
            
            (
                ffmpeg
                .input(input_path)
                .filter('crop', size, size, x_offset, y_offset)
                .output(output_path, vcodec='libx264', acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )
            
            processed_files['square'] = output_path
        
        # Corte horizontal (16:9 para 9:16)
        if video.cut_horizontal:
            output_path = os.path.join(output_dir, f"{base_name}_horizontal.mp4")
            
            # Para vídeos horizontais, criar versão vertical
            target_width = int(original_height * 9 / 16)
            x_offset = (original_width - target_width) // 2
            
            (
                ffmpeg
                .input(input_path)
                .filter('crop', target_width, original_height, x_offset, 0)
                .output(output_path, vcodec='libx264', acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )
            
            processed_files['horizontal'] = output_path
        
        # Atualizar vídeo com arquivos processados
        video.update_processing_status('processed', json.dumps(processed_files))
        db.session.commit()
        
        return True
        
    except Exception as e:
        print(f"Erro no processamento do vídeo: {e}")
        video.update_processing_status('error')
        db.session.commit()
        return False

@videos_bp.route('/videos', methods=['GET'])
def get_videos():
    """Lista todos os vídeos"""
    try:
        videos = Video.query.order_by(Video.created_at.desc()).all()
        return jsonify({
            'success': True,
            'videos': [video.to_dict() for video in videos]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@videos_bp.route('/videos/upload', methods=['POST'])
def upload_video():
    """Upload de vídeo"""
    try:
        if 'video' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo selecionado'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Formato de arquivo não suportado'
            }), 400
        
        # Verificar tamanho do arquivo
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': 'Arquivo muito grande (máximo 100MB)'
            }), 400
        
        # Salvar arquivo
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(current_app.root_path, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Adicionar timestamp ao nome do arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Extrair informações do vídeo
        video_info = get_video_info(file_path)
        
        # Obter configurações do formulário
        data = request.form
        cut_vertical = data.get('cut_vertical', 'true').lower() == 'true'
        cut_square = data.get('cut_square', 'true').lower() == 'true'
        cut_horizontal = data.get('cut_horizontal', 'false').lower() == 'true'
        caption = data.get('caption', '')
        hashtags = data.get('hashtags', '')
        
        # Criar registro no banco
        video = Video(
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            duration=video_info['duration'] if video_info else None,
            resolution=video_info['resolution'] if video_info else None,
            format=filename.rsplit('.', 1)[1].lower(),
            cut_vertical=cut_vertical,
            cut_square=cut_square,
            cut_horizontal=cut_horizontal,
            caption=caption,
            hashtags=hashtags
        )
        
        db.session.add(video)
        db.session.commit()
        
        # Processar vídeo em background (simulado)
        # Em produção, isso seria feito com Celery
        success = process_video_cuts(video.id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Vídeo enviado e processado com sucesso',
                'video': video.to_dict()
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Erro no processamento do vídeo'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@videos_bp.route('/videos/<int:video_id>/post', methods=['POST'])
def create_posting_jobs(video_id):
    """Cria jobs de postagem para um vídeo"""
    try:
        video = Video.query.get_or_404(video_id)
        
        if video.processing_status != 'processed':
            return jsonify({
                'success': False,
                'error': 'Vídeo ainda não foi processado'
            }), 400
        
        data = request.get_json()
        account_ids = data.get('account_ids', [])
        interval_minutes = data.get('interval_minutes', 5)
        
        if not account_ids:
            # Se não especificado, usar todas as contas ativas
            active_accounts = TikTokAccount.query.filter_by(status='active').all()
            account_ids = [acc.id for acc in active_accounts]
        
        if not account_ids:
            return jsonify({
                'success': False,
                'error': 'Nenhuma conta ativa disponível'
            }), 400
        
        # Obter arquivos processados
        processed_files = json.loads(video.processed_files or '{}')
        
        jobs_created = []
        current_time = datetime.utcnow()
        
        for i, account_id in enumerate(account_ids):
            # Determinar qual variante usar (prioridade: vertical > square > horizontal)
            if 'vertical' in processed_files:
                variant = 'vertical'
                file_path = processed_files['vertical']
            elif 'square' in processed_files:
                variant = 'square'
                file_path = processed_files['square']
            elif 'horizontal' in processed_files:
                variant = 'horizontal'
                file_path = processed_files['horizontal']
            else:
                continue
            
            # Calcular tempo de agendamento
            scheduled_time = current_time + timedelta(minutes=i * interval_minutes)
            
            job = PostingJob(
                video_id=video.id,
                tiktok_account_id=account_id,
                video_variant=variant,
                video_file_path=file_path,
                caption=video.caption,
                scheduled_time=scheduled_time
            )
            
            db.session.add(job)
            jobs_created.append(job)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(jobs_created)} jobs de postagem criados',
            'jobs': [job.to_dict() for job in jobs_created]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@videos_bp.route('/videos/<int:video_id>', methods=['DELETE'])
def delete_video(video_id):
    """Remove um vídeo e seus arquivos"""
    try:
        video = Video.query.get_or_404(video_id)
        
        # Verificar se há jobs pendentes
        pending_jobs = PostingJob.query.filter_by(
            video_id=video_id,
            status='pending'
        ).count()
        
        if pending_jobs > 0:
            return jsonify({
                'success': False,
                'error': f'Não é possível remover vídeo com {pending_jobs} jobs pendentes'
            }), 400
        
        # Remover arquivos físicos
        try:
            if os.path.exists(video.file_path):
                os.remove(video.file_path)
            
            # Remover arquivos processados
            if video.processed_files:
                processed_files = json.loads(video.processed_files)
                for file_path in processed_files.values():
                    if os.path.exists(file_path):
                        os.remove(file_path)
        except Exception as e:
            print(f"Erro ao remover arquivos: {e}")
        
        db.session.delete(video)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Vídeo removido com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

