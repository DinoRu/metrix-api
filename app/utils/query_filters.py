from sqlalchemy import func
from app.models.user import UserRole
from app.models.meter import Meter


def apply_department_filter(query, current_user):
    """
    Filtre les meters par département extrait de meter_id_code

    Exemple meter_id_code: DS0701OR0006383
    Département = DS07 (chars 1 à 4)
    """
    # ADMIN (DS) => accès total
    if current_user.role == UserRole.ADMIN:
        return query

    # Controller => filtrage strict par département
    if current_user.department:
        return query.where(
            func.substr(Meter.meter_id_code, 1, 4) == current_user.department
        )

    # Sécurité par défaut : rien
    return query.where(False)
