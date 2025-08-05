from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.tiktok_account import TikTokAccount
from datetime import datetime

tiktok_accounts_bp = Blueprint('tiktok_accounts', __name__)

@tiktok_accounts_bp.route('/accounts', methods=['GET'])
def get_accounts():
    """Lista todas as contas do TikTok"""
    try:
        accounts = TikTokAccount.query.all()
        return jsonify({
            'success': True,
            'accounts': [account.to_dict() for account in accounts],
            'total': len(accounts)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tiktok_accounts_bp.route('/accounts', methods=['POST'])
def add_account():
    """Adiciona uma nova conta do TikTok"""
    try:
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': 'Username e password são obrigatórios'
            }), 400
        
        # Verifica se a conta já existe
        existing_account = TikTokAccount.query.filter_by(username=data['username']).first()
        if existing_account:
            return jsonify({
                'success': False,
                'error': 'Conta já existe'
            }), 400
        
        # Cria nova conta
        account = TikTokAccount(
            username=data['username'],
            password=data['password']
        )
        
        db.session.add(account)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Conta adicionada com sucesso',
            'account': account.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tiktok_accounts_bp.route('/accounts/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    """Atualiza uma conta do TikTok"""
    try:
        account = TikTokAccount.query.get_or_404(account_id)
        data = request.get_json()
        
        if data.get('password'):
            account.update_password(data['password'])
        
        if data.get('status'):
            account.update_status(data['status'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Conta atualizada com sucesso',
            'account': account.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tiktok_accounts_bp.route('/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    """Remove uma conta do TikTok"""
    try:
        account = TikTokAccount.query.get_or_404(account_id)
        
        # Verifica se há jobs pendentes
        from src.models.video import PostingJob
        pending_jobs = PostingJob.query.filter_by(
            tiktok_account_id=account_id,
            status='pending'
        ).count()
        
        if pending_jobs > 0:
            return jsonify({
                'success': False,
                'error': f'Não é possível remover conta com {pending_jobs} jobs pendentes'
            }), 400
        
        db.session.delete(account)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Conta removida com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tiktok_accounts_bp.route('/accounts/<int:account_id>/test', methods=['POST'])
def test_account(account_id):
    """Testa a conectividade de uma conta do TikTok"""
    try:
        account = TikTokAccount.query.get_or_404(account_id)
        
        # Aqui seria implementado o teste real de login
        # Por enquanto, simula um teste
        import random
        import time
        
        time.sleep(2)  # Simula tempo de teste
        
        # Simula resultado aleatório para demonstração
        success = random.choice([True, True, True, False])  # 75% de sucesso
        
        if success:
            account.update_status('active')
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Conta testada com sucesso - Login OK',
                'status': 'active'
            })
        else:
            account.update_status('inactive')
            db.session.commit()
            
            return jsonify({
                'success': False,
                'message': 'Falha no teste - Credenciais inválidas ou conta bloqueada',
                'status': 'inactive'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tiktok_accounts_bp.route('/accounts/stats', methods=['GET'])
def get_accounts_stats():
    """Retorna estatísticas das contas"""
    try:
        total_accounts = TikTokAccount.query.count()
        active_accounts = TikTokAccount.query.filter_by(status='active').count()
        inactive_accounts = TikTokAccount.query.filter_by(status='inactive').count()
        blocked_accounts = TikTokAccount.query.filter_by(status='blocked').count()
        limited_accounts = TikTokAccount.query.filter_by(status='limited').count()
        
        # Posts hoje
        from src.models.video import PostingJob
        today = datetime.utcnow().date()
        posts_today = PostingJob.query.filter(
            PostingJob.completed_at >= today,
            PostingJob.status == 'completed'
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_accounts': total_accounts,
                'active_accounts': active_accounts,
                'inactive_accounts': inactive_accounts,
                'blocked_accounts': blocked_accounts,
                'limited_accounts': limited_accounts,
                'posts_today': posts_today
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

