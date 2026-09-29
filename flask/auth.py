"""Rôles et décorateurs d'accès, partagés par app.py et template.py."""
from functools import wraps
from flask import session, flash, redirect, url_for, abort

# Rôles reconnus par l'application, toujours en minuscules (en base, en session et dans les templates)
ROLES = ('lecture', 'modification', 'suppression', 'admin')

def normalize_roles(roles):
    """Transforme une chaîne 'LECTURE, Admin' ou une liste en liste de rôles connus,
    en minuscules, sans doublon. Les valeurs inconnues sont ignorées."""
    if not roles:
        return []
    if isinstance(roles, str):
        roles = roles.split(',')
    normalized = []
    for role in roles:
        role = (role or '').strip().lower()
        if role in ROLES and role not in normalized:
            normalized.append(role)
    return normalized

def has_role(*roles):
    """Vrai si l'utilisateur connecté possède au moins un des rôles donnés.
    - 'admin' a tous les droits ;
    - 'lecture' est accordé à tout utilisateur qui a au moins un rôle
      (on ne peut pas modifier ou supprimer ce qu'on ne peut pas voir)."""
    permissions = normalize_roles(session.get('permissions'))
    if 'admin' in permissions:
        return True
    wanted = normalize_roles(list(roles))
    if 'lecture' in wanted and permissions:
        return True
    return any(role in permissions for role in wanted)

def login_required(view_func):
    """Redirige vers la page de connexion si personne n'est connecté."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapper

def role_required(*roles):
    """Connexion obligatoire + au moins un des rôles donnés, sinon erreur 403."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(*args, **kwargs):
            if not has_role(*roles):
                abort(403)
            return view_func(*args, **kwargs)
        return wrapper
    return decorator

# Raccourci pour les routes réservées aux administrateurs
admin_required = role_required('admin')
